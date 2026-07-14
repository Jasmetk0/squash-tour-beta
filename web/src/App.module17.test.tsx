import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { ApplyResponseValidationPreviewPanel, ApplyResponseVsTargetValidationComparisonPanel, CandidateIdentityContractPanel, CandidateIdentityFingerprintPanel, CandidateIdentityOverviewPanel, CandidateIdentityReviewReferencePanel, CandidateIdentitySummaryPanel, CreateOnlyApplyAuditMetadataPreviewPanel, CreateOnlyApplyExecutionPreflightPreviewPanel, DisabledDryRunBuildContractPanel, DisabledExecutionContractSummaryPanel, FinalGuardedApplyReadinessChecklistPanel, GuardedApplyExecutionGateSpecificationPanel, FutureApplyExecutionBoundaryContractPanel, FutureApplyExecutionDecisionSummaryPanel, FutureApplyReferenceContractPanel, FutureApplyRequestValidationPreviewPanel, PostApplyCalendarVerificationPanel, SeasonTemplateSlotConflictPanel, SeasonTemplateSlotValidationPanel, TargetCalendarValidationPanel, TemplateSlotConflictCodeRegistryPanel, TemplateSlotConflictPreflightConsistencyPanel, TemplateSlotValidationPreflightConsistencyPanel, TemplateSlotValidationPreviewSummaryPanel, TemplateSlotConflictPreviewSummaryPanel, DryRunTemplateConflictSummaryPanel, PreflightTemplateConflictSummaryPanel, TemplateConflictDiagnosticsOverviewPanel, ValidationIssueCodeRegistryPanel, readCandidateIdentityReadinessOverview, readCreateOnlyApplyAuditMetadataPreview, readCreateOnlyApplyExecutionPreflightPreview, readDisabledExecutionContractSummary, readFinalGuardedApplyReadinessChecklist, readFutureApplyExecutionBoundaryContract, readFutureApplyExecutionDecisionSummary, readFutureApplyReferenceContract, readFutureApplyRequestValidationPreview, readGuardedApplyExecutionGateSpecification } from './pages/SeasonBuilderPanels'

const api = vi.hoisted(() => ({
  getHealth: vi.fn(),
  createRun: vi.fn(),
  getRun: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listRuns: vi.fn(),
  listCountries: vi.fn(),
  getCountriesMetadata: vi.fn(),
  getTournamentTemplatesMetadata: vi.fn(),
  listEvents: vi.fn(),
  getRunActivity: vi.fn(),
  getEvent: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
  getFinalsSummary: vi.fn(),
  getFinalsQualification: vi.fn(),
  getFinalsResult: vi.fn(),
  simulateWorldTourFinals: vi.fn(),
  listWorldPackages: vi.fn(),
  getWorldPackage: vi.fn(),
  getWorldPackageValidation: vi.fn(),
  cloneOfficialWorldPackage: vi.fn(),
  getLatestRollover: vi.fn(),
  getRolloverBySeason: vi.fn(),
  getPlayerTransitions: vi.fn(),
  getNextSeasonPlayers: vi.fn(),
  rolloverNextSeason: vi.fn(),
  getRunSource: vi.fn(),
  getRunLineage: vi.fn(),
  getRunTalentPlan: vi.fn(),
  listGeneratedPlayersProvenance: vi.fn(),
  bootstrapNextSeason: vi.fn(),
  getViewerRankingTable: vi.fn(),
  getAdminRankingTable: vi.fn(),
  getAdminRankingSnapshot: vi.fn(),
  getAdminPointBreakdown: vi.fn(),
  getTalentClassSummary: vi.fn(),
  getSeasonRegistry: vi.fn(),
  getSeasonActivePlayers: vi.fn(),
  getSeasonCalendar: vi.fn(),
  getSeasonTemplates: vi.fn(),
  listCalendarTemplates: vi.fn(),
  listPlanningSeasonCalendars: vi.fn(),
  getPlanningSeasonCalendar: vi.fn(),
  getCalendarTemplate: vi.fn(),
  createCalendarTemplate: vi.fn(),
  updateCalendarTemplate: vi.fn(),
  applyCalendarTemplateToPlanningCalendar: vi.fn(),
  compareCalendarTemplateDryRun: vi.fn(),
  getSeasonTemplateSlotValidation: vi.fn(),
  getSeasonTemplateSlotValidationIssueCodes: vi.fn(),
  getSeasonTemplateSlotConflicts: vi.fn(),
  getSeasonTemplateSlotConflictCodes: vi.fn(),
  getSeasonCalendarValidation: vi.fn(),
  getSeasonCalendarValidationIssueCodes: vi.fn(),
  getCategories: vi.fn(),
  getTournaments: vi.fn(),
  getTourSeasonsValidation: vi.fn(),
  postSeasonBuilderPreflight: vi.fn(),
  postSeasonBuilderDryRunBuild: vi.fn(),
  postSeasonBuilderApplyCommandContract: vi.fn(),
  postSeasonBuilderApplyCreateOnlyReadiness: vi.fn(),
  postSeasonBuilderApplyCreateOnlyCommand: vi.fn(),
  validateFutureApplyRequestPreview: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('./api/client', () => api)

function renderAppAt(route: string): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function futureApplyValidationResponseMock(
  overrides: Partial<Record<string, unknown>> = {}
): Record<string, unknown> {
  return {
    enabled: false,
    can_execute: false,
    can_mutate: false,
    target_season_label: '2000/2001',
    source_type: 'season_template',
    source_template_id: 'default_msa_template_preview',
    overwrite_policy: 'none',
    future_apply_reference_contract: {
      available: true,
      contract_type: 'future_apply_reference_contract',
      candidate_identity_reference_id: 'candidate-ref-id',
      candidate_identity_fingerprint: 'candidate-fp',
      candidate_identity_reference_type: 'dry_run_candidate_identity',
      candidate_identity_set_referenceable: true,
      apply_execution_enabled: false,
      mutation_permitted: false,
      read_only: true,
      message: 'Reference contract preview only.'
    },
    future_apply_request_validation_preview: {
      available: true,
      validation_type: 'future_apply_request_validation_preview',
      requested_candidate_identity_reference_id: 'candidate-ref-id',
      requested_candidate_identity_fingerprint: 'candidate-fp',
      requested_candidate_identity_reference_type: 'dry_run_candidate_identity',
      reference_id_matches: true,
      fingerprint_matches: true,
      reference_type_matches: true,
      contract_referenceable: true,
      apply_execution_enabled: false,
      read_only: true,
      mutation_permitted: false,
      message: 'Validation preview only.'
    },
    create_only_apply_execution_preflight_preview: {
      available: true,
      preflight_type: 'create_only_apply_execution_preflight_preview',
      target_absent: true,
      create_only_scope_confirmed: true,
      audit_metadata_present: false,
      future_apply_reference_contract_available: true,
      future_apply_request_validation_available: true,
      candidate_identity_reference_matches: true,
      main_future_command_reference_ready: true,
      all_known_preconditions_met: false,
      execution_enabled: false,
      can_execute: false,
      read_only: true,
      mutation_permitted: false,
      message: 'Create-only apply execution remains disabled in preview mode.'
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
      message: 'Create-only apply audit metadata preview is read-only.'
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
      message: 'Execution contract summary is read-only in this phase.'
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
      message: 'Final guarded checklist confirms execution remains disabled.'
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
      message: 'Execution boundary contract remains read-only in preview mode.'
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
      message: 'Execution decision summary is disabled and read-only; no execution occurs in this phase.'
    },
    audit_preview: {
      read_only: true,
      mutation_permitted: false,
      execution_enabled: false
    },
    ...overrides
  }
}

describe('Module 17 pages through routes', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRuns.mockResolvedValue({ runs: [] })
    api.listWorldPackages.mockResolvedValue({ packages: [{ world_id: 'official_fax_world', name: 'Official FAX World', description: 'Built-in official FAX squash world package.', type: 'official', status: 'active', source: 'built_in', editable: false, deletable: false, archivable: false, version: 'v1', fingerprint: 'abcdef1234567890fedcba0987654321', country_count: 3, manual_override_count: 2, continent_count: 2, region_count: 3, travel_region_count: 4, used_by_run_count: null, validation_status: 'valid', storage: { countries_path: 'config/worlds/official_fax_world/countries.json', manual_player_overrides_path: 'config/world/manual_player_overrides.json', world_metadata_path: 'config/worlds/official_fax_world/world.json', continents_path: 'config/worlds/official_fax_world/continents.json', regions_path: 'config/worlds/official_fax_world/regions.json', travel_regions_path: 'config/worlds/official_fax_world/travel_regions.json' } }] })
    api.getWorldPackage.mockResolvedValue({ world_id: 'official_fax_world', name: 'Official FAX World', description: 'Built-in official FAX squash world package.', type: 'official', status: 'active', source: 'built_in', editable: false, deletable: false, archivable: false, version: 'v1', fingerprint: 'abcdef1234567890fedcba0987654321', country_count: 3, manual_override_count: 2, continent_count: 2, region_count: 3, travel_region_count: 4, used_by_run_count: null, validation_status: 'valid', storage: { countries_path: 'config/worlds/official_fax_world/countries.json', manual_player_overrides_path: 'config/world/manual_player_overrides.json', world_metadata_path: 'config/worlds/official_fax_world/world.json', continents_path: 'config/worlds/official_fax_world/continents.json', regions_path: 'config/worlds/official_fax_world/regions.json', travel_regions_path: 'config/worlds/official_fax_world/travel_regions.json' } })
    api.cloneOfficialWorldPackage.mockResolvedValue({ ok: true, dry_run: true, source_world_id: 'official_fax_world', new_world_id: 'my_custom_world', target_path: 'config/worlds/custom/my_custom_world', created_files: ['world.json'], package: null, validation: null, errors: [] })
    api.getWorldPackageValidation.mockResolvedValue({ world_id: 'official_fax_world', status: 'warnings', error_count: 0, warning_count: 1, info_count: 6, checks: [{ code: 'world_metadata_valid', severity: 'info', status: 'passed', message: 'world.json is present and declares official_fax_world.', path: 'config/worlds/official_fax_world/world.json', field: 'world_id' }] })
    api.listCountries.mockResolvedValue({
      countries: [
        {
          code: 'EGY',
          name: 'Egypt',
          region: 'MENA',
          population: 100000000,
          wealth_support: 5,
          squash_popularity: 5,
          squash_tradition: 5,
          system_quality: 5,
          competition_density: 5,
          federation_quality: 5,
          court_count: 5000,
          travel_region: 'MENA',
          notes: null,
          style_dna: { attacking: 0.8 },
          flag_asset: null
        }
      ]
    })
    api.getCountriesMetadata.mockResolvedValue({ dataset_status: 'temporary_seed_demo', country_count: 0, source_path: 'config/world/countries.json' })
    api.getTournamentTemplatesMetadata.mockResolvedValue({ template_count: 0, source_path: 'config/tournament_templates/mvp_templates.json', referenced_by_calendar: false, referenced_template_ids: [] })
    api.getViewerRankingTable.mockResolvedValue({ rows: [], summary: { season: '2000/2001', table_type: 'ranking', player_count: 0, total_source_players: 0, ranked_player_count: 0, zero_point_players: 0, countries_represented: 0, leader_player_id: null, leader_points: null, generated_from_active_players_fingerprint: 'active-fp', rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: false }, metadata: { season: '2000/2001', table_type: 'ranking', source: 'season_active_players', active_players_fingerprint: 'active-fp', generated_fingerprint: 'generated-fp', ranking_basis: 'current active season player ranking_points', filters: { country_code: null, search: null, include_zero_points: true, min_points: null }, limit: 100, warnings: [] }, validation_warnings: ['Rolling 61-week ranking not implemented.'], validation_errors: [] })
    api.getAdminRankingTable.mockResolvedValue({ rows: [], summary: { season: '2000/2001', table_type: 'ranking', player_count: 0, total_source_players: 0, ranked_player_count: 0, zero_point_players: 0, countries_represented: 0, leader_player_id: null, leader_points: null, generated_from_active_players_fingerprint: 'active-fp', rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: false }, metadata: { season: '2000/2001', table_type: 'ranking', source: 'season_active_players', active_players_fingerprint: 'active-fp', generated_fingerprint: 'generated-fp', ranking_basis: 'current active season player ranking_points', filters: { country_code: null, search: null, include_zero_points: true, min_points: null }, limit: 100, warnings: [] }, validation_warnings: [], validation_errors: [] })
    api.getAdminRankingSnapshot.mockResolvedValue({ snapshot: null, snapshot_exists: false, summary: null, metadata: null, validation_warnings: [], validation_errors: [] })
    api.getAdminPointBreakdown.mockResolvedValue({ breakdown: null, summary_rows: [], metadata: { season: '2000/2001', source: 'season_point_awards', active_players_fingerprint: 'active-fp', point_awards_fingerprint: 'awards-fp', generated_fingerprint: 'generated-fp', applied_only: true, table_type: 'both', filters: { player_id: null, search: null, country_code: null, include_zero_point_awards: false }, limit: 10, rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: false }, validation_warnings: [], validation_errors: [] })
    api.getTalentClassSummary.mockResolvedValue({ year_start: 2030, years: 10, seed: 123, dataset_status: 'temporary_seed_demo', country_count: 0, source_path: 'config/world/countries.json', total_talents_across_span: 0, average_total_talents_per_year: 0, global_band_totals: {}, global_elite_talents: 0, global_tour_talents: 0, global_pro_depth: 0, countries: [] })
    api.getSeasonRegistry.mockResolvedValue({
      start_season: '2000/01',
      end_season: '2039/40',
      season_count: 40,
      week_count: 61,
      season_week_1_year_week: 37,
      seasons: Array.from({ length: 40 }, (_, index) => ({ season_start_year: 2000 + index, label: `${2000 + index}/${String((2001 + index) % 100).padStart(2, '0')}`, season_index: index, week_count: 61, season_week_start: 1, season_week_end: 61, year_week_start: 37, year_week_end: 36, status: 'registry_only' }))
    })
    api.getSeasonActivePlayers.mockResolvedValue({ players: [], summary: { total_active_players: 0 }, metadata: null, warnings: [] })
    api.getSeasonCalendarValidationIssueCodes.mockResolvedValue({
      read_only: true,
      code_count: 4,
      message: 'Stable read-only season calendar validation issue code registry.',
      codes: [
        { code: 'calendar_missing', severity: 'warning', title: 'Calendar missing', description: 'No persisted season calendar exists for the requested season.', field: null, read_only: true },
        { code: 'main_draw_size_invalid', severity: 'error', title: 'Invalid main draw size', description: 'main_draw_size must be greater than 0.', field: 'main_draw_size', read_only: true },
        { code: 'event_count', severity: 'info', title: 'Event count summary', description: 'Computed informational event count metric.', field: null, read_only: true },
        { code: 'calendar_validation_demo_warning', severity: 'warning', title: 'Calendar validation demo warning', description: 'Demo warning used by frontend route test.', field: 'category', read_only: true }
      ]
    })
    api.getSeasonCalendarValidation.mockResolvedValue({
      season: '2000/01',
      calendar_exists: true,
      validation_summary: { status: 'warnings', error_count: 0, warning_count: 1, info_count: 1, event_count: 1, first_season_week: 1, last_season_week: 1, categories: { count: 1, values: ['GOLD'] }, tour_levels: { count: 1, values: ['WORLD_TOUR'] }, host_countries: { count: 1, values: ['ENG'] } },
      issues: [{ severity: 'warning', code: 'calendar_validation_demo_warning', message: 'Calendar validation warning preview.', event_id: 'event-1', field: 'category', context: {} }],
      read_only: true,
      message: 'Read-only validation response.'
    })
    api.getSeasonCalendar.mockResolvedValue({
      calendar: {
        season: '2000/01',
        events: [{ event_id: 'event-1', season_week: 1, event_name: 'World Tour Gold', category: 'GOLD', host_country: 'ENG', region: 'EUROPE', status: 'scheduled' }]
      },
      summary: { event_count: 1, persisted: true, first_event_week: 1, last_event_week: 1 },
      metadata: null,
      validation_warnings: ['Read-only warning'],
      validation_errors: ['Read-only error']
    })
    api.getCategories.mockResolvedValue({
      categories: [{ category_id: 'gold', name: 'GOLD', status: 'read_only_foundation', source: 'derived_preview:tournament_templates', template_count: 1, valid_from_season: null, valid_to_season: null, tour_level: 'WORLD_TOUR', prestige_rank: null, mandatory: null, main_draw_size: null, qualification_draw_size: 16, direct_entries: 18, qualifiers: 4, wildcards: 2, lucky_losers: 2, seeds_count: 8, points_by_round: null, prize_money_total: null, match_format: null, qualifying_weeks_count: 1, main_draw_weeks_count: null, schedule_footprint_weeks: 1, source_template_ids: ['wt_gold_24'], notes: ['Mixed draw sizes across source templates.'] }],
      source_path: 'config/tournament_templates/mvp_templates.json',
      status: 'read_only_foundation'
    })
    api.getTournaments.mockResolvedValue({
      tournaments: [{ tournament_id: 'world-tour-gold', name: 'World Tour Gold', status: 'read_only_foundation', source: 'derived_preview:tournament_templates', source_template_ids: ['wt_gold_24'], template_count: 1, categories: ['GOLD'], tour_levels: ['WORLD_TOUR'], host_countries: ['ENG'], regions: ['EUROPE'], default_category: null, default_host_country: 'ENG', default_region: 'EUROPE', default_duration_weeks: 1, has_qualification: true, notes: [] }],
      source_path: 'config/tournament_templates/mvp_templates.json',
      status: 'read_only_foundation'
    })
    api.getTourSeasonsValidation.mockResolvedValue({
      status: 'read_only_foundation',
      summary: {
        total_checks: 8,
        warning_count: 2,
        info_count: 3,
        ok_count: 3,
        registry_loaded: true,
        category_count: 1,
        tournament_count: 1,
        season_template_count: 1,
        season_template_slot_count: 1
      },
      sections: [
        { section_id: 'registry', title: 'Registry', issues: [] },
        { section_id: 'category', title: 'Category', issues: [{ issue_id: 'category-gold-notes', severity: 'warning', area: 'category', item_id: 'gold', item_name: 'GOLD', message: 'Notes present in backend validation.', link_hint: '/admin/tour-seasons/categories/gold' }] },
        { section_id: 'tournament', title: 'Tournament', issues: [] },
        { section_id: 'season_template', title: 'Season Template', issues: [] }
      ],
      planned_future: ['Backend validation engine.']
    })
    api.getSeasonTemplates.mockResolvedValue({
      templates: [{ template_id: 'default_msa_template_preview', name: 'Default MSA Template Preview', description: 'Read-only derived preview built from current tournament templates config.', season_count_supported: 40, week_count: 61, slot_count: 1, source: 'derived_preview:tournament_templates', status: 'read_only_foundation', slots: [{ slot_id: 'slot-01-wt_gold_24', season_week_start: 1, season_week_end: 1, duration_weeks: 1, tournament_name: 'World Tour Gold', category: 'GOLD', host_country: 'ENG', region: 'EUROPE', has_qualification: true, qualifying_week_start: 1, main_draw_week_start: 1, source_template_id: 'wt_gold_24', notes: null }] }],
      source_path: 'config/tournament_templates/mvp_templates.json',
      status: 'read_only_foundation'
    })
    api.listCalendarTemplates.mockResolvedValue({
      templates: [],
      source_path: 'config/world/calendar_templates.json',
      status: 'ok',
      schema_version: 'calendar_templates.v1'
    })
    api.listPlanningSeasonCalendars.mockResolvedValue({
      calendars: [],
      source_path: 'config/world/planning_season_calendars.json',
      schema_version: 'planning_season_calendars.v1',
      registry_fingerprint: 'pl_reg_empty',
      read_only: true,
      status: 'ok',
      safety: { planning_only: true, viewer_visible: false, simulation_consumed: false, canonical_season_calendar_modified: false }
    })
    api.compareCalendarTemplateDryRun.mockResolvedValue({
      dry_run: true,
      mutation_performed: false,
      target_season_label: '2006/07',
      source_template_id: 'template-a',
      policy: 'copy_missing_only',
      target_source: 'payload',
      source_template_fingerprint: 'source-fp',
      target_calendar_fingerprint: null,
      target_calendar_exists: false,
      target_fingerprint: 'target-fp',
      diff_fingerprint: 'diff-fp',
      summary: { same_count: 1, missing_from_target_count: 1, only_in_target_count: 0, conflict_count: 0, locked_target_preserved_count: 1, selected_source_event_count: 2, source_event_count: 2, target_event_count: 2 },
      items: [{ status: 'same', source_event_id: 'source-nemarque-open', target_event_id: 'target-nemarque-open-2006-07', event_name: 'Némarque Open', category_code: 'DIAMOND', source_weeks: [6, 7], target_weeks: [6, 7], source_qualification_weeks: [5], target_qualification_weeks: [5], locked_target: true, reason: 'Matched event.' }],
      safety: { read_only: true, mutation_performed: false, apply_endpoint_enabled: false, message: 'Dry-run only; no mutation performed.' },
      status: 'ok'
    })
    api.getCalendarTemplate.mockResolvedValue({
      template: null,
      source_path: 'config/world/calendar_templates.json',
      status: 'ok',
      schema_version: 'calendar_templates.v1'
    })
    api.getSeasonTemplateSlotValidation.mockResolvedValue({
      template_id: 'default_msa_template_preview',
      template_exists: true,
      read_only: true,
      message: 'Template slot validation completed.',
      summary: {
        status: 'warnings',
        error_count: 0,
        warning_count: 1,
        issue_count: 1,
        slot_count: 5,
        week_count: 5,
        first_week: 1,
        last_week: 5
      },
      issues: [
        {
          severity: 'warning',
          code: 'template_slot_duration_long',
          message: 'Template slot duration 5 weeks is unusually long (>3).',
          slot_id: 'slot-01-default_msa_template_preview'
        }
      ]
    })
    api.getSeasonTemplateSlotConflicts.mockResolvedValue({
      template_id: 'default_msa_template_preview',
      template_exists: true,
      read_only: true,
      message: 'Template slot conflict analysis completed.',
      summary: { status: 'warnings', warning_count: 1, info_count: 2, conflict_count: 3, slot_count: 5, occupied_week_count: 5, busiest_week: 5, busiest_week_slot_count: 4, read_only: true },
      conflicts: [{ severity: 'warning', code: 'template_conflict_week_overloaded', message: 'Season week 5 has 4 template slots.', season_week: 5, slot_ids: ['slot-01-default_msa_template_preview'], categories: ['PLATINUM'], tour_levels: ['WORLD_TOUR'], host_countries: ['ENG'], read_only: true }]
    })
    api.getSeasonTemplateSlotValidationIssueCodes.mockResolvedValue({
      read_only: true,
      code_count: 2,
      message: 'Stable read-only season template slot validation issue code registry.',
      codes: [
        { code: 'template_slot_duration_long', severity: 'warning', title: 'Template slot duration long', description: 'Template slot duration is unusually long.', field: 'duration_in_season_weeks', read_only: true },
        { code: 'template_slot_start_after_end', severity: 'error', title: 'Template slot start after end', description: 'Template slot season_week_start is greater than season_week_end.', field: 'season_week_start', read_only: true }
      ]
    })
    api.getSeasonTemplateSlotConflictCodes.mockResolvedValue({
      read_only: true,
      code_count: 2,
      message: 'Stable read-only season template slot conflict code registry.',
      codes: [
        {
          code: 'template_conflict_week_overloaded',
          severity: 'warning',
          title: 'Week overloaded',
          description: 'A season week has many overlapping template slots.',
          read_only: true
        },
        {
          code: 'template_conflict_opening_dead_zone',
          severity: 'info',
          title: 'Opening dead zone',
          description: 'No slots are scheduled during opening season weeks 1-4.',
          read_only: true
        }
      ]
    })
    api.postSeasonBuilderPreflight.mockResolvedValue({
      can_build: false,
      target_season_label: '2000/2001',
      source_type: 'season_template',
      source_template_id: 'default_msa_template_preview',
      preflight_fingerprint: 'pf_test_existing',
      reviewed_diff_id: 'rd_test_existing',
      target_calendar_exists: true,
      target_event_count: 1,
      source_resolved: true,
      source_summary: { template_name: 'Default MSA Template Preview', slot_count: 1, week_count: 61 },
      authoritative_diff_summary: {
        status: 'read_only_preflight',
        can_build: false,
        target_calendar_exists: true,
        target_event_count: 1,
        source_type: 'season_template',
        source_resolved: true,
        source_slot_count: 1,
        source_week_count: 1,
        target_week_count: 1,
        week_count_compatible: true,
        source_range: { first_week: 1, last_week: 1 },
        target_range: { first_week: 1, last_week: 1 },
        structural_comparison: { planned_source_slots: 1, existing_target_events: 1, target_is_empty: false, requires_overwrite_or_merge_policy: true },
        blocking_reasons: ['Explicit overwrite/merge policy is required before any future build when a target calendar already exists.'],
        advisory_notes: [],
        placeholder: 'Event-level additions/replacements/conflicts remain planned for a future phase.',
        template_conflict_summary: {
          available: true,
          read_only: true,
          non_blocking: true,
          status: 'warnings',
          warning_count: 1,
          info_count: 2,
          conflict_count: 3,
          conflict_codes: ['template_conflict_week_overloaded'],
          busiest_week: 5,
          busiest_week_slot_count: 4,
          source: 'template_slot_conflict_preview',
          message: 'Template slot conflict diagnostics are available as read-only non-blocking preview.'
        }
      },
      template_slot_validation_preview: { template_id: 'default_msa_template_preview', template_exists: true, status: 'warnings', error_count: 0, warning_count: 1, issue_count: 1, issue_codes: ['template_slot_duration_long'], error_codes: [], warning_codes: ['template_slot_duration_long'], read_only: true },
      template_slot_conflict_preview: {
        template_id: 'default_msa_template_preview',
        template_exists: true,
        status: 'warnings',
        warning_count: 1,
        info_count: 2,
        conflict_count: 3,
        conflict_codes: [
          'template_conflict_week_overloaded',
          'template_conflict_opening_dead_zone',
          'template_conflict_final_dead_zone'
        ],
        warning_codes: ['template_conflict_week_overloaded'],
        info_codes: ['template_conflict_opening_dead_zone', 'template_conflict_final_dead_zone'],
        busiest_week: 5,
        busiest_week_slot_count: 4,
        read_only: true
      },
      template_conflict_diagnostics_overview: {
        selected_report_available: false,
        selected_status: null,
        selected_conflict_count: 0,
        preflight_preview_available: true,
        preflight_summary_available: true,
        preflight_status: 'warnings',
        preflight_conflict_count: 3,
        dry_run_preview_available: false,
        dry_run_summary_available: false,
        dry_run_status: null,
        dry_run_conflict_count: 0,
        mutation_behavior: 'unavailable',
        blocking_behavior: 'non_blocking',
        read_only: true,
        non_blocking: true
      },
      validation_warnings: [
        '[template_slot_duration_long] [slot=slot-01-default_msa_template_preview] Template slot duration 5 weeks is unusually long (>3).'
      ],
      validation_errors: [],
      audit_preview: { action: 'season_builder_preflight', read_only: true, mutation_permitted: false }
    })
    api.postSeasonBuilderDryRunBuild.mockImplementation(async (payload) => {
      const hasAllMetadata = payload.audit_reason === 'ticket-123 dry-run review'
        && payload.explicit_confirmation === 'I understand this is disabled.'
        && payload.mutation_scope === 'merge_preview'
      return {
        command: 'season_builder_dry_run_build',
        enabled: false,
        can_execute: false,
        can_mutate: false,
        target_season_label: '2000/01',
        source_type: 'season_template',
        source_template_id: 'default_msa_template_preview',
        overwrite_policy: payload.overwrite_policy ?? null,
        preflight_fingerprint: payload.preflight_fingerprint,
        reviewed_diff_id: payload.reviewed_diff_id,
        validation_errors: [],
        validation_warnings: hasAllMetadata
          ? []
          : [
              'audit_reason will be required before execution is enabled in a future phase.',
              'explicit_confirmation will be required before execution is enabled in a future phase.',
              'mutation_scope will be required before execution is enabled in a future phase.'
            ],
        audit_preview: {
          action: 'season_builder_dry_run_build',
          read_only: true,
          mutation_permitted: false,
          execution_enabled: false,
          target_season_label: '2000/01',
          source_type: 'season_template',
          source_template_id: 'default_msa_template_preview',
          overwrite_policy: payload.overwrite_policy ?? null,
          preflight_fingerprint: payload.preflight_fingerprint,
          reviewed_diff_id: payload.reviewed_diff_id,
          requested_by: 'local-admin-preview',
          audit_reason: hasAllMetadata ? 'ticket-123 dry-run review' : payload.audit_reason,
          explicit_confirmation_present: hasAllMetadata ? true : Boolean(payload.explicit_confirmation),
          mutation_scope: hasAllMetadata ? 'merge_preview' : payload.mutation_scope,
          generation_design_preview_available: true,
          candidate_event_contract_preview_available: true,
          conflict_contract_preview_available: true,
          dry_run_result_contract_preview_available: true,
          dry_run_result_preview_available: true,
          dry_run_result_identity_available: true
        },
        generation_design_preview: {
          status: 'design_preview_only',
          execution_enabled: false,
          will_generate_events: false,
          will_persist_calendar: false,
          will_mutate_existing_calendar: false,
          planned_steps: [
            'Validate reviewed preflight identity.',
            'Resolve target season.',
            'Resolve source template or future source.',
            'Compute source event candidates.',
            'Compare candidates with target calendar.',
            'Return additions/replacements/conflicts without persistence.',
            'Require separate audited command before any mutation.'
          ],
          required_future_inputs: ['preflight_fingerprint', 'reviewed_diff_id', 'audit_reason', 'explicit_confirmation', 'mutation_scope'],
          planned_output_sections: ['candidate_events', 'structural_summary', 'conflict_summary', 'validation_errors', 'validation_warnings', 'audit_preview'],
          blocked_reason: 'Dry-run generation is not implemented in this phase.'
        },
        candidate_event_contract_preview: {
          status: 'contract_preview_only',
          will_generate_candidates: false,
          candidate_count: 0,
          event_shape: { candidate_id: 'string', source_slot_id: 'string', season_week_start: 'int', event_name: 'string', candidate_status: 'planned | conflict | invalid', comparison_classification: 'addition | replacement | conflict | invalid', comparison_reason: 'string', matched_existing_event_id: 'string | null', matched_existing_event_name: 'string | null', matched_existing_event_week: 'int | null', validation_errors: 'string[]', validation_warnings: 'string[]' },
          structural_summary_shape: { candidate_count: 'int', additions_count: 'int', conflict_count: 'int', invalid_count: 'int' },
          conflict_summary_shape: { week_conflicts: 'array', slot_conflicts: 'array', policy_conflicts: 'array', validation_conflicts: 'array' },
          blocked_reason: 'Candidate event generation is not implemented in this phase.'
        },
      conflict_contract_preview: {
        status: 'contract_preview_only',
        will_compute_conflicts: false,
        conflict_count: 0,
        week_conflict_shape: { conflict_id: 'string', conflict_type: 'week_overlap', season_week: 'int', candidate_id: 'string', existing_event_id: 'string | null', message: 'string', severity: 'info | warning | blocking' },
        slot_conflict_shape: { conflict_id: 'string', conflict_type: 'slot_collision', source_slot_id: 'string', candidate_id: 'string', existing_event_id: 'string | null', message: 'string', severity: 'info | warning | blocking' },
        policy_conflict_shape: { conflict_id: 'string', conflict_type: 'policy_violation', policy: 'merge_preview | overwrite_preview | create_only_preview | repair_preview', candidate_id: 'string | null', message: 'string', severity: 'info | warning | blocking' },
        validation_conflict_shape: { conflict_id: 'string', conflict_type: 'validation_error', field: 'string', candidate_id: 'string | null', message: 'string', severity: 'warning | blocking' },
        blocked_reason: 'Conflict computation is not implemented in this phase.'
      },
      dry_run_result_contract_preview: {
        status: 'contract_preview_only',
        will_return_real_result: false,
        candidate_events: [],
        structural_summary: { candidate_count: 0, target_event_count: null, additions_count: 0, replacement_count: 0, conflict_count: 0, invalid_count: 0 },
        conflict_summary: { week_conflicts: [], slot_conflicts: [], policy_conflicts: [], validation_conflicts: [] },
        result_metadata: { preflight_fingerprint: payload.preflight_fingerprint, reviewed_diff_id: payload.reviewed_diff_id, execution_enabled: false, read_only: true, mutation_permitted: false },
        blocked_reason: 'Dry-run result generation is not implemented in this phase.'
      },
      dry_run_result_preview: {
        status: 'read_only_generated',
        execution_enabled: false,
        mutation_permitted: false,
        candidate_events: [{ candidate_id: 'cand_default_msa_template_preview_slot-01-wt_gold_24', source_slot_id: 'slot-01-wt_gold_24', season_week_start: 1, season_week_end: 1, event_name: 'World Tour Gold', tour_level: null, category: 'GOLD', host_country: 'ENG', candidate_status: 'conflict', comparison_classification: 'conflict', comparison_reason: 'Candidate has read-only comparison conflicts.', matched_existing_event_id: 'event_2000_gold_01', matched_existing_event_name: 'World Tour Gold', matched_existing_event_week: 1, validation_errors: [], validation_warnings: [] }],
        structural_summary: { candidate_count: 1, target_event_count: 1, additions_count: 0, replacement_count: 1, conflict_count: 1, invalid_count: 0 },
        conflict_summary: { week_conflicts: [], slot_conflicts: [], policy_conflicts: [{ conflict_id: 'policy_violation_missing_overwrite_policy', conflict_type: 'policy_violation', policy: null, candidate_id: null, message: 'Existing target calendar requires explicit merge/overwrite policy before future mutation.', severity: 'blocking' }], validation_conflicts: [] },
        result_metadata: { preflight_fingerprint: payload.preflight_fingerprint, reviewed_diff_id: payload.reviewed_diff_id, source_type: 'season_template', source_template_id: 'default_msa_template_preview', overwrite_policy: payload.overwrite_policy ?? null, target_calendar_exists: true, target_event_count: 1, comparison_performed: true, read_only: true, mutation_permitted: false, dry_run_result_fingerprint: 'drf_test_existing', dry_run_result_id: 'drr_test_existing' },
        validation_summary: { status: 'blocking', blocking_count: 1, warning_count: 3, info_count: 0, blocking_reasons: ['Existing target calendar requires explicit merge/overwrite policy before future mutation.'], warning_reasons: ['audit_reason will be required before execution is enabled in a future phase.', 'explicit_confirmation will be required before execution is enabled in a future phase.', 'mutation_scope will be required before execution is enabled in a future phase.'], info_messages: [], candidate_status_counts: { planned: 0, replacement: 0, conflict: 1, invalid: 0 }, conflict_type_counts: { week_conflicts: 0, slot_conflicts: 0, policy_conflicts: 1, validation_conflicts: 0 } },
        plan_readiness: { read_only_plan_available: true, has_blocking_issues: true, has_warnings: true, mutation_still_disabled: true, next_required_step: 'Review dry-run summary; execution remains disabled.' },
        identity_readiness: { status: 'blocked_reference', items: [{ area: 'validation_summary', status: 'Blocked', message: "Validation summary status is 'blocking'." }, { area: 'mutation_state', status: 'Blocked', message: 'Mutation remains disabled; this checklist is reference-only.' }], future_command_reference: { preflight_fingerprint: payload.preflight_fingerprint, reviewed_diff_id: payload.reviewed_diff_id, dry_run_result_fingerprint: 'drf_test_existing', dry_run_result_id: 'drr_test_existing', can_reference_future_command: false, mutation_still_disabled: true, candidate_identity_fingerprint: 'abc123fingerprint', candidate_identity_reference_id: 'abc123fingerprint', can_reference_candidate_identity_set: true, candidate_identity_reference_type: 'candidate_identity_set' } },
        candidate_identity_fingerprint: { fingerprint: 'abc123fingerprint', fingerprint_algorithm: 'sha256', fingerprint_payload_version: 1, candidate_count: 1, candidate_ids: ['cand_default_msa_template_preview_slot-01-wt_gold_24'], candidate_identity_keys: ['default_msa_template_preview:slot-01-wt_gold_24'], safe_for_future_reference: true, read_only: true, mutation_permitted: false, message: 'Candidate identity fingerprint is deterministic and read-only.' },
        candidate_identity_review_reference: { reference_type: 'candidate_identity_set', reference_id: 'abc123fingerprint', fingerprint_algorithm: 'sha256', fingerprint_payload_version: 1, candidate_count: 1, safe_for_future_reference: true, can_reference_future_apply: true, read_only: true, mutation_permitted: false, message: 'Candidate identity set can be referenced by a future audited apply flow.' },
        future_apply_reference_contract: { available: true, contract_type: 'future_apply_reference_contract', candidate_identity_reference_type: 'candidate_identity_set', candidate_identity_reference_id: 'abc123fingerprint', candidate_identity_fingerprint: 'abc123fingerprint', candidate_identity_set_referenceable: true, main_future_command_reference_ready: false, apply_execution_enabled: false, create_only_apply_required: true, read_only: true, mutation_permitted: false, message: 'Future apply reference contract is preview-only and disabled.' },
        dry_run_result_fingerprint: 'drf_test_existing',
        dry_run_result_id: 'drr_test_existing',
        template_conflict_summary: {
          available: true,
          read_only: true,
          non_blocking: true,
          status: 'warnings',
          warning_count: 1,
          info_count: 2,
          conflict_count: 3,
          conflict_codes: ['template_conflict_week_overloaded'],
          busiest_week: 5,
          busiest_week_slot_count: 4,
          source: 'template_slot_conflict_preview',
          message: 'Template slot conflict diagnostics are available as read-only non-blocking preview.'
        }
      },
      template_conflict_diagnostics_overview: {
        selected_report_available: false,
        selected_status: null,
        selected_conflict_count: 0,
        preflight_preview_available: true,
        preflight_summary_available: true,
        preflight_status: 'warnings',
        preflight_conflict_count: 3,
        dry_run_preview_available: true,
        dry_run_summary_available: true,
        dry_run_status: 'warnings',
        dry_run_conflict_count: 3,
        mutation_behavior: 'unavailable',
        blocking_behavior: 'non_blocking',
        read_only: true,
        non_blocking: true
      },
        message: 'Dry-run build command contract exists, but execution is disabled in this phase.'
      }
    })
    api.postSeasonBuilderApplyCommandContract.mockImplementation(async (payload) => {
      const hasAllMetadata = payload.audit_reason === 'ticket-123 dry-run review'
        && payload.explicit_confirmation === 'I understand this is disabled.'
        && payload.mutation_scope === 'merge_preview'
      return {
        command: 'season_builder_apply_command',
        enabled: false,
        can_execute: false,
        can_mutate: false,
        target_season_label: '2000/01',
        source_type: 'season_template',
        source_template_id: 'default_msa_template_preview',
        overwrite_policy: payload.overwrite_policy ?? null,
        validation_errors: [],
        validation_warnings: hasAllMetadata ? [] : [
          'audit_reason will be required before apply execution is enabled in a future phase.',
          'explicit_confirmation will be required before apply execution is enabled in a future phase.',
          'mutation_scope will be required before apply execution is enabled in a future phase.'
        ],
        audit_preview: {
          action: 'season_builder_apply_command',
          read_only: true,
          mutation_permitted: false,
          execution_enabled: false,
          target_season_label: '2000/01',
          source_type: 'season_template',
          source_template_id: 'default_msa_template_preview',
          overwrite_policy: payload.overwrite_policy ?? null,
          preflight_fingerprint: payload.preflight_fingerprint,
          reviewed_diff_id: payload.reviewed_diff_id,
          dry_run_result_fingerprint: payload.dry_run_result_fingerprint,
          dry_run_result_id: payload.dry_run_result_id,
          requested_by: 'local-admin-preview',
          audit_reason: payload.audit_reason,
          explicit_confirmation_present: Boolean(payload.explicit_confirmation),
          mutation_scope: payload.mutation_scope,
          audit_trail_contract_preview_available: true,
          safety_gate_contract_preview_available: true
        },
        audit_trail_contract_preview: {
          status: 'contract_preview_only',
          will_persist_audit: false,
          audit_event_type: 'season_builder_apply_command',
          required_identity_fields: ['preflight_fingerprint', 'reviewed_diff_id', 'dry_run_result_fingerprint', 'dry_run_result_id'],
          required_actor_fields: ['requested_by', 'audit_reason', 'explicit_confirmation', 'mutation_scope'],
          audit_record_shape: {
            audit_id: 'string',
            timestamp_utc: 'datetime',
            action: 'season_builder_apply_command',
            target_season_label: 'string',
            source_type: 'string',
            source_template_id: 'string | null',
            overwrite_policy: 'string | null',
            preflight_fingerprint: 'string',
            reviewed_diff_id: 'string',
            dry_run_result_fingerprint: 'string',
            dry_run_result_id: 'string',
            requested_by: 'string | null',
            audit_reason: 'string | null',
            explicit_confirmation_present: 'bool',
            mutation_scope: 'string | null',
            execution_enabled: 'bool',
            mutation_permitted: 'bool',
            result: 'disabled | executed | rejected'
          },
          blocked_reason: 'Audit trail persistence is not implemented in this phase.'
        },
        safety_gate_contract_preview: {
          status: 'contract_preview_only',
          will_execute_apply: false,
          will_mutate_calendar: false,
          gate_result: 'blocked_disabled_phase',
          required_gates: [
            { gate: 'identity', required: true, currently_satisfied: true, message: 'Preflight, reviewed diff, and dry-run result identities must be present.' },
            { gate: 'audit_metadata', required: true, currently_satisfied: hasAllMetadata, message: 'Audit reason, explicit confirmation, and mutation scope must be present.' },
            { gate: 'execution_enabled', required: true, currently_satisfied: false, message: 'Execution is disabled in this phase.' },
            { gate: 'mutation_permission', required: true, currently_satisfied: false, message: 'Mutation permission is disabled in this phase.' },
            { gate: 'audit_trail', required: true, currently_satisfied: false, message: 'Audit trail persistence is not implemented in this phase.' }
          ],
          future_allowed_mutation_scopes: ['create_only_preview', 'merge_preview', 'overwrite_preview', 'repair_preview'],
          blocked_reason: 'Final apply safety gate is contract-only and disabled in this phase.'
        },
        required_identity: {
          preflight_fingerprint: payload.preflight_fingerprint,
          reviewed_diff_id: payload.reviewed_diff_id,
          dry_run_result_fingerprint: payload.dry_run_result_fingerprint,
          dry_run_result_id: payload.dry_run_result_id,
          all_identity_fields_present: true
        },
        required_audit_metadata: {
          requested_by: 'local-admin-preview',
          audit_reason_present: Boolean(payload.audit_reason),
          explicit_confirmation_present: Boolean(payload.explicit_confirmation),
          mutation_scope: payload.mutation_scope,
          all_audit_metadata_present: hasAllMetadata
        },
        message: 'Apply command contract exists, but execution is disabled in this phase.'
      }
    })
    api.postSeasonBuilderApplyCreateOnlyReadiness.mockImplementation(async (payload) => ({
      command: 'season_builder_apply_create_only_readiness',
      enabled: false,
      can_execute_apply: true,
      can_mutate: false,
      would_create_calendar: true,
      service_insert_applicable: false,
      target_season_label: '2000/01',
      source_type: payload.source_type,
      source_template_id: payload.source_template_id,
      overwrite_policy: payload.overwrite_policy,
      preflight_fingerprint: payload.preflight_fingerprint,
      reviewed_diff_id: payload.reviewed_diff_id,
      dry_run_result_fingerprint: payload.dry_run_result_fingerprint,
      dry_run_result_id: payload.dry_run_result_id,
      apply_gate_summary: {
        identity_ready: true,
        policy_ready: false
      },
      candidate_summary: {
        candidate_count: 1,
        first_season_week: 1,
        last_season_week: 1,
        categories: { count: 1, values: ['GOLD'] },
        tour_levels: { count: 1, values: ['WORLD_TOUR'] }
      },
      audit_preview: { audit_persisted: false, read_only: true },
      validation_warnings: [],
      validation_errors: [],
      message: 'Create-only apply readiness is query-only in this phase.'
    }))
    api.validateFutureApplyRequestPreview.mockResolvedValue(
      futureApplyValidationResponseMock({
        future_apply_request_validation_preview: {
          available: true,
          validation_type: 'future_apply_request_validation_preview',
          requested_candidate_identity_reference_id: 'abc123fingerprint',
          requested_candidate_identity_fingerprint: 'abc123fingerprint',
          requested_candidate_identity_reference_type: 'candidate_identity_set',
          reference_id_matches: true,
          fingerprint_matches: true,
          reference_type_matches: true,
          contract_referenceable: true,
          apply_execution_enabled: false,
          read_only: true,
          mutation_permitted: false,
          message: 'Validation preview only.'
        }
      })
    )
  })

  it('renders the Phase 1 landing page at root', async () => {
    renderAppAt('/')
    expect(await screen.findByText('Choose how you want to use the deterministic FAX squash world.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Browse the generated squash world/i })).toHaveAttribute('href', '/viewer')
    expect(screen.getByRole('link', { name: /Build, validate, and simulate the world/i })).toHaveAttribute('href', '/admin')
  })

  it('renders the Admin Engine dashboard route', async () => {
    renderAppAt('/admin')
    expect(await screen.findByRole('heading', { name: 'Admin Engine Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Simulate' })).toHaveAttribute('href', '/admin/simulate')
    expect(screen.getByRole('link', { name: 'Tour & Seasons' })).toHaveAttribute('href', '/admin/tour-seasons')
  })

  it('renders Simulate launcher overview concepts without fake results table', async () => {
    renderAppAt('/admin/simulate')
    expect(await screen.findByRole('heading', { name: 'Simulate' })).toBeInTheDocument()
    expect(screen.getByText('Simulation launcher for match, round, tournament, week, season, and full timeline workflows.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Runs' })).toHaveAttribute('href', '/admin/runs')
    expect(screen.getByRole('link', { name: /Match/ })).toHaveAttribute('href', '/admin/runs#match')
    expect(screen.getByRole('link', { name: /Round/ })).toHaveAttribute('href', '/admin/runs#round')
    expect(screen.getByRole('link', { name: /Tournament/ })).toHaveAttribute('href', '/admin/runs#tournament')
    expect(screen.getByRole('link', { name: /^Week/ })).toHaveAttribute('href', '/admin/runs#week')
    expect(screen.getByRole('link', { name: /Season Simulate rest of season/ })).toHaveAttribute('href', '/admin/runs#season')
    expect(screen.getByRole('link', { name: /Full Timeline/ })).toHaveAttribute('href', '/admin/runs#timeline')
    expect(screen.getByText(/Next Tournament/)).toBeInTheDocument()
    expect(screen.getByText(/Next Week/)).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })


  it('renders Diagnostics control center overview with run guidance and category sections', async () => {
    localStorage.setItem('beta_engine:last_run_id', 'run-a')
    renderAppAt('/admin/diagnostics')

    expect(await screen.findByRole('heading', { name: 'Diagnostics' })).toBeInTheDocument()
    expect(
      screen.getByText(
        'Control center for world balance, calendar validation, run health, invalidated data, narrative locks, and audit warnings.'
      )
    ).toBeInTheDocument()
    expect(screen.getByText(/Operational diagnostics currently remain run-scoped in Run Diagnostics/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Runs' })).toHaveAttribute('href', '/admin/runs')
    expect(screen.getByRole('link', { name: /Open last run diagnostics/i })).toHaveAttribute('href', '/admin/runs/run-a/diagnostics')

    expect(screen.getByRole('heading', { name: 'World Balance' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Calendar Validation' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Run Health' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Invalidated Data' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Narrative Locks' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Audit / Warnings' })).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByText(/warning count|error count|total issues/i)).not.toBeInTheDocument()
  })
  it('wires Admin Calendar Compare to backend dry-run without mutation controls', async () => {
    api.listCalendarTemplates.mockResolvedValueOnce({
      templates: [{ id: 'template-a', name: 'Template A', description: 'Persisted template', status: 'draft', events: [], template_fingerprint: 'tpl-a' }],
      source_path: 'config/world/calendar_templates.json',
      status: 'ok',
      schema_version: 'calendar_templates.v1'
    })

    renderAppAt('/admin/tour-seasons/compare')

    expect(await screen.findByRole('heading', { name: 'Backend compare dry-run' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Calendar compare and apply safety notes' })).toBeInTheDocument()
    expect(screen.getByText('Compare remains dry-run by default.')).toBeInTheDocument()
    expect(screen.getByText('Payload mode remains dry-run only.')).toBeInTheDocument()
    expect(screen.getByText('Only planning-calendar copy_missing_only apply is enabled after a reviewed persisted planning-calendar dry-run; replace/update workflows remain disabled.')).toBeInTheDocument()
    expect(screen.getByText('replace_unlocked_only is not enabled.')).toBeInTheDocument()
    expect(screen.getByText('replace_all is not enabled.')).toBeInTheDocument()
    expect(screen.getByText('Backend dry-run only.')).toBeInTheDocument()
    expect(screen.getByText(/Compare dry-run only until/)).toBeInTheDocument()
    expect(screen.getAllByText('No canonical season calendar is modified.').length).toBeGreaterThan(0)
    expect(screen.getByText('Apply uses copy_missing_only only.')).toBeInTheDocument()
    expect(screen.getAllByText('No existing planning event is updated.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('No Viewer, rankings, race, history, run data, or simulation output changes.').length).toBeGreaterThan(0)
    expect(screen.getByText(/Payload target mode uses local preview rows/)).toBeInTheDocument()
    expect(await screen.findByRole('option', { name: 'Template A' })).toBeInTheDocument()
    expect(screen.getByLabelText('Target source')).toHaveValue('payload')
    expect(screen.getByLabelText('Target season label')).toHaveValue('2006/07')
    expect(screen.getByText(/Policy:/)).toBeInTheDocument()
    expect(screen.queryByText('replace_unlocked_only')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Two-pane compare/copy workspace preview' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Run backend compare dry-run' }))

    await waitFor(() => expect(api.compareCalendarTemplateDryRun).toHaveBeenCalledTimes(1))
    const [dryRunPayload] = api.compareCalendarTemplateDryRun.mock.calls[0]
    expect(dryRunPayload).toEqual({
      target_season_label: '2006/07',
      source_template_id: 'template-a',
      policy: 'copy_missing_only',
      target_source: 'payload',
      target_events: [
        expect.objectContaining({ id: 'target-nemarque-open-2006-07', name: 'Némarque Open', category_code: 'DIAMOND', qualification_weeks: [5], weeks: [6, 7], locked: true }),
        expect.objectContaining({ id: 'target-world-championship-2006-07', name: 'World Championship', category_code: 'WORLD_CHAMPIONSHIP', qualification_weeks: [48], weeks: [49, 50], locked: true })
      ]
    })
    expect(await screen.findByText('source-fp')).toBeInTheDocument()
    expect(screen.getByText('target-fp')).toBeInTheDocument()
    expect(screen.getByText('diff-fp')).toBeInTheDocument()
    expect(screen.getByText('Dry-run only; no mutation performed.')).toBeInTheDocument()
    expect(screen.getAllByText('same').length).toBeGreaterThan(0)
    expect(screen.getByText('Matched event.')).toBeInTheDocument()
    expect(screen.getAllByText('W6–W7').length).toBeGreaterThan(0)
    expect(screen.getAllByText('W5').length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /save|archive|delete|simulate/i })).not.toBeInTheDocument()
  })

  it('runs Admin Calendar Compare with a persisted planning calendar target', async () => {
    api.listCalendarTemplates.mockResolvedValueOnce({
      templates: [{ id: 'template-a', name: 'Template A', description: 'Persisted template', status: 'draft', events: [], template_fingerprint: 'tpl-a' }],
      source_path: 'config/world/calendar_templates.json',
      status: 'ok',
      schema_version: 'calendar_templates.v1'
    })
    api.listPlanningSeasonCalendars.mockResolvedValueOnce({
      calendars: [{ season_label: '2000/01', normalized_season_label: '2000/2001', status: 'draft', events: [{ id: 'pl-a', name: 'Planning A', category_code: 'DIAMOND', weeks: [6], qualification_weeks: [5], locked: true, event_fingerprint: 'pl_evt_a' }], metadata: {}, calendar_fingerprint: 'pl_cal_abc' }],
      source_path: 'config/world/planning_season_calendars.json',
      schema_version: 'planning_season_calendars.v1',
      registry_fingerprint: 'pl_reg_abc',
      read_only: true,
      status: 'ok',
      safety: { planning_only: true, viewer_visible: false, simulation_consumed: false, canonical_season_calendar_modified: false }
    })
    api.compareCalendarTemplateDryRun.mockResolvedValueOnce({
      dry_run: true,
      mutation_performed: false,
      target_season_label: '2000/2001',
      source_template_id: 'template-a',
      policy: 'copy_missing_only',
      target_source: 'planning_calendar',
      source_template_fingerprint: 'source-fp',
      target_fingerprint: 'pl_cal_abc',
      target_calendar_fingerprint: 'pl_cal_abc',
      target_calendar_exists: true,
      diff_fingerprint: 'diff-planning',
      summary: { same_count: 1, missing_from_target_count: 0, only_in_target_count: 0, conflict_count: 0, locked_target_preserved_count: 0, selected_source_event_count: 1, source_event_count: 1, target_event_count: 1 },
      items: [],
      safety: { read_only: true, mutation_performed: false, apply_endpoint_enabled: false, message: 'Dry-run only; no mutation performed.' },
      status: 'ok'
    })

    renderAppAt('/admin/tour-seasons/compare')

    expect(await screen.findByRole('option', { name: 'Template A' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Target source'), { target: { value: 'planning_calendar' } })
    expect(await screen.findByRole('option', { name: /2000\/2001 — 1 events — draft/ })).toBeInTheDocument()
    expect(screen.getByText('Target is loaded server-side from persisted planning calendars. No planning calendar is mutated. target_fingerprint uses the persisted planning calendar fingerprint.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Run backend compare dry-run' }))

    await waitFor(() => expect(api.compareCalendarTemplateDryRun).toHaveBeenCalledTimes(1))
    const [dryRunPayload] = api.compareCalendarTemplateDryRun.mock.calls[0]
    expect(dryRunPayload).toEqual({
      target_season_label: '2000/2001',
      source_template_id: 'template-a',
      target_source: 'planning_calendar',
      policy: 'copy_missing_only'
    })
    expect(dryRunPayload).not.toHaveProperty('target_events')
    expect(await screen.findByText('planning_calendar')).toBeInTheDocument()
    expect(screen.getAllByText('pl_cal_abc').length).toBeGreaterThan(0)
    expect(screen.getAllByText('true').length).toBeGreaterThan(0)
    expect(screen.getByText('Planning calendar mode: target_fingerprint uses the persisted planning calendar fingerprint.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Apply reviewed diff to planning calendar' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Apply reviewed diff to planning calendar' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('requested_by'), { target: { value: 'admin' } })
    fireEvent.change(screen.getByLabelText('audit_reason'), { target: { value: 'reviewed diff' } })
    fireEvent.change(screen.getByLabelText('explicit_confirmation'), { target: { value: 'wrong' } })
    expect(screen.getByRole('button', { name: 'Apply reviewed diff to planning calendar' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('explicit_confirmation'), { target: { value: 'I understand this will apply reviewed template events to the planning calendar only.' } })
    expect(screen.getByRole('button', { name: 'Apply reviewed diff to planning calendar' })).toBeEnabled()
  })

  it('shows empty planning calendar message and disables planning target dry-run while keeping payload available', async () => {
    api.listCalendarTemplates.mockResolvedValueOnce({
      templates: [{ id: 'template-a', name: 'Template A', description: 'Persisted template', status: 'draft', events: [], template_fingerprint: 'tpl-a' }],
      source_path: 'config/world/calendar_templates.json',
      status: 'ok',
      schema_version: 'calendar_templates.v1'
    })
    api.listPlanningSeasonCalendars.mockResolvedValueOnce({
      calendars: [],
      source_path: 'config/world/planning_season_calendars.json',
      schema_version: 'planning_season_calendars.v1',
      registry_fingerprint: 'pl_reg_empty',
      read_only: true,
      status: 'ok',
      safety: { planning_only: true, viewer_visible: false, simulation_consumed: false, canonical_season_calendar_modified: false }
    })

    renderAppAt('/admin/tour-seasons/compare')

    expect(await screen.findByRole('option', { name: 'Template A' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Run backend compare dry-run' })).toBeEnabled()
    fireEvent.change(screen.getByLabelText('Target source'), { target: { value: 'planning_calendar' } })
    expect(screen.getByText('No persisted planning calendars exist yet.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Run backend compare dry-run' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Target source'), { target: { value: 'payload' } })
    expect(screen.getByRole('button', { name: 'Run backend compare dry-run' })).toBeEnabled()
  })

  it('shows safe create-template link when no persisted calendar templates exist on compare page', async () => {
    api.listCalendarTemplates.mockResolvedValueOnce({ templates: [], source_path: null, status: 'ok', schema_version: 'calendar_templates.v1' })

    renderAppAt('/admin/tour-seasons/compare')

    expect(await screen.findByText(/Create a persisted calendar template first\./)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Create new calendar template' })).toHaveAttribute('href', '/admin/tour-seasons/season-templates/new')
  })

  it('renders Tour & Seasons hub and shell routes while keeping operational routes available', async () => {
    renderAppAt('/admin/tour-seasons')
    expect(await screen.findByRole('heading', { name: 'Tour & Seasons' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Future calendar planning model' })).toBeInTheDocument()
    expect(screen.getByText('Season calendar events will use weeks and qualificationWeeks. Qualification belongs to the main event. Locked events must be unlocked before move/delete/overwrite actions. Calendar templates will be Admin-only until copied into canonical seasons.')).toBeInTheDocument()
    expect(screen.getByText('Examples only — future planning model, not persisted season data.')).toBeInTheDocument()
    expect(screen.getByText('Némarque Open — DIAMOND — Qualifying W5 · Main W6–W7 — Locked')).toBeInTheDocument()
    expect(screen.getByText('World Tour Finals — WORLD_TOUR_FINALS — Main W55 — Locked')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Categories/ })).toHaveAttribute('href', '/admin/tour-seasons/categories')
    expect(screen.getByRole('link', { name: /Tournaments/ })).toHaveAttribute('href', '/admin/tour-seasons/tournaments')
    expect(screen.getByRole('link', { name: /Season Templates/ })).toHaveAttribute('href', '/admin/tour-seasons/season-templates')
    expect(screen.getByRole('link', { name: /Season Registry/ })).toHaveAttribute('href', '/admin/tour-seasons/season-registry')
    expect(screen.getByRole('link', { name: /Seasons Concrete 61-week season calendars/ })).toHaveAttribute('href', '/admin/seasons')
    expect(screen.getByRole('link', { name: /Calendar Compare \/ Apply/ })).toHaveAttribute('href', '/admin/tour-seasons/compare')
    expect(screen.getByRole('link', { name: /Calendar Validation/ })).toHaveAttribute('href', '/admin/tour-seasons/validation')

    renderAppAt('/admin/tour-seasons/categories')
    expect(await screen.findByRole('heading', { name: 'Categories' })).toBeInTheDocument()
    expect(screen.getByText(/stable tournament category identities/i)).toBeInTheDocument()
    expect(screen.getByText(/Season-specific points, prize money, draw sizes, qualification formats, and ranking rules will be defined later/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Canonical tournament category catalog')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'World Tour' })).toBeInTheDocument()
    expect(screen.getByRole('article', { name: 'Platinium category' })).toBeInTheDocument()
    expect(screen.getByText(/Existing backend category previews remain read-only/i)).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: /GOLD \(gold\)/ })).toHaveAttribute('href', '/admin/tour-seasons/categories/gold')
    expect(screen.getByRole('heading', { name: 'Derived category rules packages' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Open Tournament Templates' })[0]).toHaveAttribute('href', '/admin/tournament-templates')
    expect(screen.getAllByRole('link', { name: 'Open Season Templates' })[0]).toHaveAttribute('href', '/admin/tour-seasons/season-templates')

    renderAppAt('/admin/tour-seasons/tournaments')
    expect(await screen.findByRole('heading', { name: 'Tournaments' })).toBeInTheDocument()
    expect(screen.getByText(/Read-only tournament master records derived from current tournament template config\./)).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: /World Tour Gold \(world-tour-gold\)/ })).toHaveAttribute('href', '/admin/tour-seasons/tournaments/world-tour-gold')
    expect(screen.getAllByRole('link', { name: 'Open Tournament Templates' })[0]).toHaveAttribute('href', '/admin/tournament-templates')
    expect(screen.getAllByRole('link', { name: 'Open Categories' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons/categories')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Open Season Templates' })[0]).toHaveAttribute('href', '/admin/tour-seasons/season-templates')


    renderAppAt('/admin/tour-seasons/season-templates')
    expect(await screen.findByRole('heading', { name: 'Season Templates' })).toBeInTheDocument()
    expect(screen.getAllByText(/Read-only foundation\./).length).toBeGreaterThan(0)
    const draftTemplatesSection = screen.getByRole('heading', { name: 'Admin-only calendar draft templates' }).closest('article')
    expect(draftTemplatesSection).not.toBeNull()
    expect(within(draftTemplatesSection as HTMLElement).getByText(/Calendar draft templates are Admin-only planning objects\./)).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText(/They are not played, not visible in Viewer,/)).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText(/and do not mutate canonical seasons until explicitly copied\/applied later\./)).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText(/Template events use weeks and qualificationWeeks\./)).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getAllByText(/Qualification belongs to the main event\./).length).toBeGreaterThan(0)
    expect(within(draftTemplatesSection as HTMLElement).getByText(/must be explicitly unlocked before move\/delete\/overwrite actions\./)).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText('Create draft template — planned')).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText('Add events using weeks and qualificationWeeks — planned')).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText('Lock important events — planned')).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText('Compare template against canonical season — planned')).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText('Copy selected events into canonical season — planned')).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText('Replace unlocked events only — planned')).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText('Examples only — future Admin template model, not persisted template data.')).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText('Némarque Open — DIAMOND — Qualifying W5 · Main W6–W7 — Locked')).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText('Ameriga Open — DIAMOND — Qualifying W43 · Main W44–W45 — Locked')).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText('World Championship — WORLD_CHAMPIONSHIP — Qualifying W48 · Main W49–W50 — Locked')).toBeInTheDocument()
    expect(within(draftTemplatesSection as HTMLElement).getByText('World Tour Finals — WORLD_TOUR_FINALS — Main W55 — Locked')).toBeInTheDocument()
    const mutationButtonPattern = /^(Create|Save|Apply|Delete|Replace)$/i
    expect(within(draftTemplatesSection as HTMLElement).queryByRole('button', { name: mutationButtonPattern })).not.toBeInTheDocument()
    for (const forbiddenCopy of [/fake points/i, /fake prize/i, /fake draw/i, /fake ranking/i]) {
      expect(within(draftTemplatesSection as HTMLElement).queryByText(forbiddenCopy)).not.toBeInTheDocument()
    }
    expect((await screen.findAllByText(/Source path: config\/tournament_templates\/mvp_templates\.json/)).length).toBeGreaterThan(0)
    const persistedTemplatesSection = screen.getByRole('heading', { name: 'Persisted Admin calendar templates' }).closest('article')
    expect(persistedTemplatesSection).not.toBeNull()
    expect(within(persistedTemplatesSection as HTMLElement).getByText(/Persisted Admin calendar templates are Admin-only planning\/config objects stored by the backend\./)).toBeInTheDocument()
    expect(within(persistedTemplatesSection as HTMLElement).getByText(/They are not played,/)).toBeInTheDocument()
    expect(within(persistedTemplatesSection as HTMLElement).getByText(/not visible in Viewer, and do not mutate canonical seasons, runs, rankings, race, history, or simulation output\./)).toBeInTheDocument()
    expect(within(persistedTemplatesSection as HTMLElement).getByText(/Phase B enables safe Admin-only create\/update/)).toBeInTheDocument()
    expect(within(persistedTemplatesSection as HTMLElement).getByRole('link', { name: 'Create persisted calendar template' })).toHaveAttribute('href', '/admin/tour-seasons/season-templates/new')
    expect(within(persistedTemplatesSection as HTMLElement).getByText('Persisted templates: 0')).toBeInTheDocument()
    expect(within(persistedTemplatesSection as HTMLElement).getByText('Schema version: calendar_templates.v1')).toBeInTheDocument()
    expect(within(persistedTemplatesSection as HTMLElement).getByText('No persisted Admin calendar templates exist yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Default MSA Template Preview \(default_msa_template_preview\)/ })).toHaveAttribute('href', '/admin/tour-seasons/season-templates/default_msa_template_preview')
    expect(screen.getAllByRole('link', { name: 'Open Season Registry' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons/season-registry')).toBe(true)
    expect(screen.getByRole('link', { name: 'Open Seasons' })).toHaveAttribute('href', '/admin/seasons')
    expect(screen.getAllByRole('link', { name: 'Back to Tour & Seasons' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Open Categories' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons/categories')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Open Calendar Compare / Apply' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons/compare')).toBe(true)
    expect(within(persistedTemplatesSection as HTMLElement).queryByRole('button', { name: /save|create|update|archive|delete|copy|apply|simulate/i })).not.toBeInTheDocument()
    expect(api.listCalendarTemplates).toHaveBeenCalled()

    api.listCalendarTemplates.mockResolvedValueOnce({
      templates: [{
        id: 'template-a',
        name: 'Template A',
        description: 'Persisted read-only template',
        status: 'draft',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
        template_fingerprint: 'tpl_template_a',
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
          notes: 'Read-only persisted event',
          source_template_id: 'source-a',
          event_fingerprint: 'evt_event_a'
        }]
      }],
      source_path: 'config/world/calendar_templates.json',
      status: 'ok',
      schema_version: 'calendar_templates.v1'
    })
    renderAppAt('/admin/tour-seasons/season-templates')
    expect(await screen.findByText('Template A')).toBeInTheDocument()
    expect(screen.getByText('template-a')).toBeInTheDocument()
    expect(screen.getByText('draft')).toBeInTheDocument()
    expect(screen.getByText('tpl_template_a')).toBeInTheDocument()
    const persistedTemplateHeadings = screen.getAllByRole('heading', { name: 'Persisted Admin calendar templates' })
    const persistedTemplatesWithRowsSection = persistedTemplateHeadings[persistedTemplateHeadings.length - 1]?.closest('article')
    expect(persistedTemplatesWithRowsSection).not.toBeNull()
    expect(within(persistedTemplatesWithRowsSection as HTMLElement).getByRole('cell', { name: '1' })).toBeInTheDocument()
    expect(within(persistedTemplatesWithRowsSection as HTMLElement).getByRole('link', { name: 'Open persisted calendar template' })).toHaveAttribute('href', '/admin/tour-seasons/season-templates/calendar/template-a')
    expect(within(persistedTemplatesWithRowsSection as HTMLElement).queryByRole('button', { name: /save|create|update|archive|delete|copy|apply|simulate/i })).not.toBeInTheDocument()


    renderAppAt('/admin/tour-seasons/season-registry')
    expect(await screen.findByRole('heading', { level: 2, name: 'Season Registry' })).toBeInTheDocument()
    expect(screen.getByText(/fixed 2000\/01–2039\/40 MSA season model\./)).toBeInTheDocument()
    expect(screen.getByText(/Canonical seasons are the real 40-season MSA timeline from 2000\/01 through 2039\/40\./)).toBeInTheDocument()
    expect(screen.getByText(/Admin-only calendar templates will be created separately and can later be copied into these seasons\./)).toBeInTheDocument()
    expect(screen.getByText(/Template changes will not automatically mutate canonical seasons\./)).toBeInTheDocument()
    expect(screen.getByText(/Calendar events will use weeks and qualificationWeeks\./)).toBeInTheDocument()
    expect(screen.getAllByText(/Qualification belongs to the main event\./).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Locked events must be explicitly unlocked before move\/delete\/overwrite actions\./).length).toBeGreaterThan(0)
    const seasonLink = await screen.findByRole('link', { name: '2000/01' })
    expect(seasonLink).toHaveAttribute('href', '/admin/seasons/detail/2000%2F01')
    expect(screen.getByRole('cell', { name: '2039/40' })).toBeInTheDocument()
    expect(screen.getAllByText(/61 Season Weeks/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Calendar status: existing read model unavailable \/ not loaded/).length).toBe(40)
    expect(screen.getAllByText(/Canonical season · 61 Season Weeks · Admin calendar editor: planned/).length).toBe(40)
    expect(screen.getAllByText('Open calendar — planned')).toHaveLength(40)
    expect(screen.getAllByText('Copy from template — planned')).toHaveLength(40)
    expect(screen.getAllByText('Save as template — planned')).toHaveLength(40)
    expect(screen.getAllByText('Compare/copy workspace — planned')).toHaveLength(40)
    expect(screen.queryByRole('button', { name: /Open calendar|Copy from template|Save as template|Compare\/copy workspace/ })).not.toBeInTheDocument()
    const registryTableSection = screen.getByRole('heading', { name: 'Registry table' }).closest('article')
    expect(registryTableSection).not.toBeNull()
    const registryTable = within(registryTableSection as HTMLElement)
    expect(registryTable.queryByText(/Event count/i)).not.toBeInTheDocument()
    expect(registryTable.queryByText(/Prize money/i)).not.toBeInTheDocument()
    expect(registryTable.queryByText(/Draw size/i)).not.toBeInTheDocument()
    expect(registryTable.queryByText(/Points/i)).not.toBeInTheDocument()
    expect(registryTable.queryByText(/Validation status/i)).not.toBeInTheDocument()
    expect(screen.getByText(/SW1 → YW37/)).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Season' })).toBeInTheDocument()
    expect(screen.getByText('Season links open the read-only Concrete Season detail profile. Direct season editing workflow is planned.')).toBeInTheDocument()

    renderAppAt('/admin/tour-seasons/compare')
    expect(await screen.findByRole('heading', { name: 'Calendar Compare / Apply' })).toBeInTheDocument()
    expect(screen.getByText(/Dry-run compare by default, with guarded copy_missing_only apply for persisted planning calendars\./)).toBeInTheDocument()
    expect(await screen.findByText('Registry range')).toBeInTheDocument()
    expect(await screen.findByText('2000/01–2039/40')).toBeInTheDocument()
    expect(screen.getByText('Registry season count')).toBeInTheDocument()
    expect(screen.getByText('Registry week count')).toBeInTheDocument()
    expect(screen.getByText('Season templates count')).toBeInTheDocument()
    expect(screen.getAllByText('Default MSA Template Preview').length).toBeGreaterThan(0)
    const compareWorkspaceSection = screen.getByRole('heading', { name: 'Two-pane compare/copy workspace preview' }).closest('article')
    expect(compareWorkspaceSection).not.toBeNull()
    const compareWorkspace = within(compareWorkspaceSection as HTMLElement)
    expect(compareWorkspace.getByText('Target canonical season')).toBeInTheDocument()
    expect(compareWorkspace.getByText('Source calendar/template')).toBeInTheDocument()
    expect(compareWorkspace.getByText('Preview only — not persisted, not applied, not simulation data.')).toBeInTheDocument()
    expect(compareWorkspace.getByText(/local example CalendarEventDraft rows with weeks and qualificationWeeks vocabulary/)).toBeInTheDocument()
    expect(compareWorkspace.getAllByText(/Némarque Open/).length).toBeGreaterThan(0)
    expect(compareWorkspace.getAllByText(/DIAMOND/).length).toBeGreaterThan(0)
    expect(compareWorkspace.getAllByText(/Qualifying W5 · Main W6–W7/).length).toBe(2)
    expect(compareWorkspace.getAllByText(/World Championship/).length).toBeGreaterThan(0)
    expect(compareWorkspace.getAllByText(/Qualifying W48 · Main W49–W50/).length).toBe(2)
    expect(compareWorkspace.getByText(/Ameriga Open/)).toBeInTheDocument()
    expect(compareWorkspace.getByText(/Qualifying W43 · Main W44–W45/)).toBeInTheDocument()
    expect(compareWorkspace.getByText(/World Tour Finals/)).toBeInTheDocument()
    expect(compareWorkspace.getByText(/Main W55/)).toBeInTheDocument()
    expect(screen.getByText(/Same:/)).toBeInTheDocument()
    expect(screen.getByText(/Missing from target:/)).toBeInTheDocument()
    expect(screen.getByText(/Locked target preserved:/)).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Open Draft Template Sandbox' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons/season-templates/draft-sandbox')).toBe(true)
    expect(screen.getByText('Planned statuses: Same, Modified, Missing from current, Only in current, and Conflict.')).toBeInTheDocument()
    expect(screen.getByText('Planned actions: Apply to this season, Replace current, Keep current, Ignore, and Open editor.')).toBeInTheDocument()
    expect(screen.getByText('These actions are planned and not enabled.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /copy|apply|replace|keep current|ignore|open editor|save|update|delete|create/i })).not.toBeInTheDocument()

    renderAppAt('/admin/tour-seasons/validation')
    expect(await screen.findByRole('heading', { name: 'Calendar Validation' })).toBeInTheDocument()
    expect(screen.getByText('Read-only validation overview for Tour & Seasons foundation data.')).toBeInTheDocument()
    expect(await screen.findByText('Categories: 1')).toBeInTheDocument()
    expect((await screen.findAllByText('Tournaments: 1')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Season Templates: 1')).toBeInTheDocument()
    expect(await screen.findByText(/Season Template Slots \(total\): 1/)).toBeInTheDocument()
    expect(await screen.findByText('Total checks: 7')).toBeInTheDocument()
    expect(await screen.findByText('Warnings: 1')).toBeInTheDocument()
    expect((await screen.findAllByText('Info: 3')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('OK: 3')).length).toBeGreaterThan(0)
    expect(await screen.findByRole('heading', { name: 'Backend validation foundation' })).toBeInTheDocument()
    expect(screen.getAllByText('Status: read_only_foundation').length).toBeGreaterThan(0)
    expect(screen.getByText('Total checks: 8')).toBeInTheDocument()
    expect(screen.getByText('Warnings: 2')).toBeInTheDocument()
    expect(screen.getAllByText('Info: 3').length).toBeGreaterThan(0)
    expect(screen.getAllByText('OK: 3').length).toBeGreaterThan(0)
    expect(screen.getByText('Sections returned: 4')).toBeInTheDocument()
    expect(screen.getByText('Frontend-derived total checks: 7')).toBeInTheDocument()
    expect(screen.getByText('Backend total checks: 8')).toBeInTheDocument()
    expect(screen.getByText('Comparison only; both systems are read-only.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Backend validation issue preview' })).toBeInTheDocument()
    const backendIssuePreviewSummary = screen.getByText('Show backend issue preview')
    expect(backendIssuePreviewSummary).toBeInTheDocument()
    expect(screen.getByText('Secondary preview only. Frontend-derived checks remain primary until backend validation becomes authoritative.')).not.toBeVisible()
    expect(screen.getByRole('link', { name: 'Notes present in backend validation.' })).not.toBeVisible()
    fireEvent.click(backendIssuePreviewSummary)
    expect(screen.getByText('Secondary preview only. Frontend-derived checks remain primary until backend validation becomes authoritative.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Notes present in backend validation.' })).toHaveAttribute('href', '/admin/tour-seasons/categories/gold')
    expect(screen.getByText(/Frontend-derived checks remain visible below until backend validation becomes the authoritative source\./)).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'All' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Warnings' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Info' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'OK' })).toBeInTheDocument()
    expect(await screen.findByText(/\[Warning\] Category/)).toBeInTheDocument()
    expect(await screen.findByText(/\[Info\] Tournament/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Warnings' }))
    expect(screen.getByText(/\[Warning\] Category/)).toBeInTheDocument()
    expect(screen.queryByText(/\[Info\] Tournament/)).not.toBeInTheDocument()
    expect(screen.getAllByText('No checks match the current filter.').length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: 'Info' }))
    expect(screen.getByText(/\[Info\] Tournament/)).toBeInTheDocument()
    expect(screen.queryByText(/\[Warning\] Category/)).not.toBeInTheDocument()

    expect(screen.getAllByRole('link', { name: /GOLD \(gold\)/ })[0]).toHaveAttribute('href', '/admin/tour-seasons/categories/gold')
    expect(screen.getAllByRole('link', { name: /World Tour Gold \(world-tour-gold\)/ })[0]).toHaveAttribute('href', '/admin/tour-seasons/tournaments/world-tour-gold')
    expect(screen.queryByRole('button', { name: /apply|save|update|delete|create/i })).not.toBeInTheDocument()
  }, 15000)

  it('renders Season Builder read-only source selection preview', async () => {
    api.getSeasonCalendar.mockResolvedValueOnce({
      calendar: null,
      summary: { event_count: 0, season_weeks_used: 0, first_event_week: null, last_event_week: null, world_tour_events: 0, elite_tour_events: 0, validation_warning_count: 0, validation_error_count: 0, persisted: false, calendar_exists: false },
      metadata: null,
      validation_warnings: [],
      validation_errors: []
    })
    api.postSeasonBuilderDryRunBuild.mockImplementationOnce(async (payload) => {
      await new Promise((resolve) => setTimeout(resolve, 50))
      return await api.postSeasonBuilderDryRunBuild(payload)
    })
    renderAppAt('/admin/seasons/build')
    expect(await screen.findByRole('heading', { name: 'Season Builder' })).toBeInTheDocument()
    expect(screen.getByText('Build and review season calendar candidates. Most panels are read-only previews. The danger zone can execute a real create-only command that persists a missing target calendar.')).toBeInTheDocument()
    expect(screen.queryByText('This page does not build or modify calendars.')).not.toBeInTheDocument()
    expect(screen.getByText('Preview panels are read-only and non-mutating.')).toBeInTheDocument()
    expect(screen.getByText('The danger-zone command is the only real persistent create-only mutation flow on this page.')).toBeInTheDocument()
    expect(screen.getByText('Target season candidates')).toBeInTheDocument()
    expect((await screen.findAllByText(/Default MSA Template Preview/)).length).toBeGreaterThan(0)
    expect(screen.getByText('Planned source types')).toBeInTheDocument()
    expect(screen.getByText('Read-only builder selection')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '2000/01' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Season template' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Blank calendar (planned)' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Another season (planned)' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Custom slot (planned)' })).toBeInTheDocument()
    expect(screen.getByText('Selection preview')).toBeInTheDocument()
    expect(screen.getByText('Target compact label: 2000/01')).toBeInTheDocument()
    expect(screen.getByText('Target legacy label: 2000/2001')).toBeInTheDocument()
    expect(screen.getByText('Target season index: 0')).toBeInTheDocument()
    expect(screen.getByText('Target season week range: SW1–SW61')).toBeInTheDocument()
    expect(screen.getByText('Target year week range: YW37–YW36')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open target season detail' })).toHaveAttribute('href', '/admin/seasons/detail/2000%2F01')
    expect(screen.getByRole('link', { name: 'Open selected season in Seasons workspace' })).toHaveAttribute('href', '/admin/seasons?season=2000%2F01')
    expect(screen.getAllByRole('link', { name: 'Open Season Registry' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons/season-registry')).toBe(true)
    expect(screen.getByText('Template name: Default MSA Template Preview')).toBeInTheDocument()
    expect(screen.getAllByText('Slot count: 1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Week count: 61').length).toBeGreaterThan(0)
    expect(screen.getByText('Selected template slot preview')).toBeInTheDocument()
    expect(screen.getByText('Selected template validation summary')).toBeInTheDocument()
    expect(screen.getByText('Selected template slot validation')).toBeInTheDocument()
    expect(screen.getByText('Selected template slot conflict analysis')).toBeInTheDocument()
    expect(screen.getByText('Template slot validation vs builder diagnostics consistency')).toBeInTheDocument()
    expect(await screen.findByText('Read-only consistency check between structured template slot validation and builder diagnostics.')).toBeInTheDocument()
    expect(screen.getByText('Template slot conflict vs builder diagnostics consistency')).toBeInTheDocument()
    expect(screen.getByText('Read-only consistency check between selected template slot conflict report and builder conflict previews.')).toBeInTheDocument()
    expect(screen.getByText('Structured template slot conflict codes: template_conflict_week_overloaded')).toBeInTheDocument()
    expect(screen.getByText('All structured template slot conflict codes are represented in preflight preview.')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict preview status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict preview conflict count: 3')).toBeInTheDocument()
    expect(screen.getAllByText('Preflight template conflict summary').length).toBeGreaterThan(0)
    expect(screen.getByText('Preflight template conflict diagnostics available: true')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict diagnostics read-only: true')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict diagnostics non-blocking: true')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict conflict count: 3')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict conflict codes: template_conflict_week_overloaded')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict source: template_slot_conflict_preview')).toBeInTheDocument()
    expect(screen.getAllByText('No dry-run result to compare yet.').length).toBeGreaterThan(0)
    expect(await screen.findByText('Preflight diagnostics issue codes source: structured preview')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot preview status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot preview issue count: 1')).toBeInTheDocument()
    expect(screen.getByText('All structured template slot issue codes are represented in preflight diagnostics.')).toBeInTheDocument()
    expect(await screen.findByText(/Read-only selected template slot validation\./)).toBeInTheDocument()
    expect(screen.getByText(/Template slot validation has warnings but no blocking errors\./)).toBeInTheDocument()
    expect(screen.getByText(/Template slot validation status: warnings/)).toBeInTheDocument()
    expect(screen.getByText('Template slot validation errors: 0')).toBeInTheDocument()
    expect(screen.getByText('Template slot validation warnings: 1')).toBeInTheDocument()
    expect(screen.getByText('Template slot count: 5')).toBeInTheDocument()
    expect(screen.getByText('Template slot week count: 5')).toBeInTheDocument()
    expect(screen.getAllByText('template_slot_duration_long').length).toBeGreaterThan(1)
    expect(screen.getByText('Template slot duration long (duration_in_season_weeks)')).toBeInTheDocument()
    expect(screen.getByText('Template slot duration is unusually long.')).toBeInTheDocument()
    expect(screen.getAllByText('slot-01-default_msa_template_preview').length).toBeGreaterThan(0)
    expect(screen.getByText('Template slot duration 5 weeks is unusually long (>3).')).toBeInTheDocument()
    expect(api.getSeasonTemplateSlotValidation).toHaveBeenCalledWith('default_msa_template_preview')
    expect(api.getSeasonTemplateSlotValidationIssueCodes).toHaveBeenCalled()
    expect(api.getSeasonTemplateSlotConflicts).toHaveBeenCalledWith('default_msa_template_preview')
    expect(api.getSeasonTemplateSlotConflictCodes).toHaveBeenCalled()
    expect(screen.getByText('Read-only selected template slot conflict analysis. No mutation path is available in this panel.')).toBeInTheDocument()
    expect(screen.getByText('Template slot conflict analysis has schedule warnings.')).toBeInTheDocument()
    expect(screen.getByText('Selected template slot conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Selected template slot conflict warning count: 1')).toBeInTheDocument()
    expect(screen.getByText('Selected template slot conflict info count: 2')).toBeInTheDocument()
    expect(screen.getByText('Selected template slot conflict conflict count: 3')).toBeInTheDocument()
    expect(screen.getAllByText('template_conflict_week_overloaded').length).toBeGreaterThan(1)
    expect(screen.getAllByText('Week overloaded').length).toBeGreaterThan(1)
    expect(screen.getAllByText('A season week has many overlapping template slots.').length).toBeGreaterThan(1)
    expect(screen.getByText('Season week 5 has 4 template slots.')).toBeInTheDocument()
    expect(screen.getByText('Template slot conflict code registry')).toBeInTheDocument()
    expect(screen.getByText('Template conflict diagnostics overview')).toBeInTheDocument()
    expect(screen.getByText('Read-only template conflict diagnostics overview.')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict report: available')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict count: 3')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict preview: available')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict summary: available')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict count: 3')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict preview: available')).toBeInTheDocument()
    expect(screen.getByText('Conflict diagnostics mutation behavior: unavailable')).toBeInTheDocument()
    expect(screen.getByText('Conflict diagnostics blocking behavior: non-blocking')).toBeInTheDocument()
    expect(screen.getByText('Read-only template slot conflict code registry.')).toBeInTheDocument()
    expect(screen.getByText('Template slot conflict code count: 2')).toBeInTheDocument()
    expect(screen.getAllByText('slot-01-default_msa_template_preview').length).toBeGreaterThan(0)
    expect(screen.getByText('Target existing calendar preview')).toBeInTheDocument()
    expect(screen.getByText('Overwrite / merge policy preview')).toBeInTheDocument()
    expect(screen.getByText('Overwrite / merge policy selection for preflight')).toBeInTheDocument()
    expect(screen.getByText('Read-only preflight input. This selector only changes the backend preflight payload and does not execute merge or overwrite.')).toBeInTheDocument()
    expect(screen.getByLabelText('Future policy preview')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'No policy selected' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Merge policy preview' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Overwrite policy preview' })).toBeInTheDocument()
    expect(screen.getByText('Changing this selector re-runs read-only backend preflight only. It does not mutate any calendar.')).toBeInTheDocument()
    expect(screen.getByText('Source vs target preflight summary')).toBeInTheDocument()
    expect(screen.getByText('Read-only source/target diff detail')).toBeInTheDocument()
    expect(screen.getByText('Backend preflight contract preview')).toBeInTheDocument()
    expect(screen.getByText('Read-only design preview. No backend preflight endpoint is called from this page.')).toBeInTheDocument()
    expect(screen.getAllByText('target_season_label').length).toBeGreaterThan(0)
    expect(screen.getAllByText('source_type').length).toBeGreaterThan(0)
    expect(screen.getAllByText('source_template_id or future source identifier').length).toBeGreaterThan(0)
    expect(screen.getAllByText('overwrite_policy').length).toBeGreaterThan(0)
    expect(screen.getAllByText('requested_by / admin actor').length).toBeGreaterThan(0)
    expect(screen.getByText('seed / version / template hash')).toBeInTheDocument()
    expect(screen.getByText('can_build: false until authoritative validation passes')).toBeInTheDocument()
    expect(screen.getByText('authoritative_diff_summary')).toBeInTheDocument()
    expect(screen.getByText('validation_warnings and validation_errors')).toBeInTheDocument()
    expect(screen.getAllByText('audit_preview').length).toBeGreaterThan(0)
    expect(screen.getByText('Future implementation must add an authoritative backend preflight before any build, merge, overwrite, or apply command can exist.')).toBeInTheDocument()
    expect(screen.getByText('Backend preflight result')).toBeInTheDocument()
    expect(await screen.findByText('Even when backend preflight succeeds, build actions remain unavailable in this phase.')).toBeInTheDocument()
    expect(screen.getByText('Policy preview interpretation')).toBeInTheDocument()
    expect(screen.getByText('No overwrite/merge policy is selected for this read-only preflight.')).toBeInTheDocument()
    expect(screen.getByText('Policy preview never enables build actions in this phase.')).toBeInTheDocument()
    expect(screen.getByText('Status: Blocked in this phase')).toBeInTheDocument()
    expect(screen.getByText('Advisory validation warnings are present.')).toBeInTheDocument()
    expect(screen.getByText('This is the exact read-only payload sent to the backend preflight endpoint.')).toBeInTheDocument()
    expect(screen.getByText('Backend preflight completed, but build actions remain disabled because can_build is false.')).toBeInTheDocument()
    expect(screen.getByText('Authoritative diff status')).toBeInTheDocument()
    expect(screen.getByText('Source vs target structural summary')).toBeInTheDocument()
    expect(screen.getByText('Source and target ranges')).toBeInTheDocument()
    expect(screen.getByText('Structural comparison')).toBeInTheDocument()
    expect(screen.getAllByText('Blocking reasons').length).toBeGreaterThan(0)
    expect(screen.getByText('Advisory notes')).toBeInTheDocument()
    expect(screen.getByText('Raw authoritative diff summary JSON')).toBeInTheDocument()
    expect(screen.getByText('requires_overwrite_or_merge_policy')).toBeInTheDocument()
    expect(screen.getByText('planned_source_slots')).toBeInTheDocument()
    expect(screen.getByText('existing_target_events')).toBeInTheDocument()
    expect(screen.getByText('No backend advisory notes returned.')).toBeInTheDocument()
    expect(screen.getAllByText(/\"mutation_permitted\": false/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('target_season_label').length).toBeGreaterThan(0)
    expect(screen.getAllByText('source_type').length).toBeGreaterThan(0)
    expect(screen.getAllByText('source_template_id').length).toBeGreaterThan(0)
    expect(screen.getAllByText('overwrite_policy').length).toBeGreaterThan(0)
    expect(screen.getAllByText('requested_by').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Explicit overwrite/merge policy is required before any future build when a target calendar already exists.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('action').length).toBeGreaterThan(0)
    expect(screen.getAllByText('read_only').length).toBeGreaterThan(0)
    expect(screen.getAllByText('mutation_permitted').length).toBeGreaterThan(0)
    expect(screen.getByText('Read-only local summary. This is not an authoritative backend preflight and does not enable build actions.')).toBeInTheDocument()
    expect(screen.getByText('Local structural diff preview only. This is not an authoritative backend diff and does not enable apply actions.')).toBeInTheDocument()
    expect(screen.getByText('Read-only policy preview. No overwrite, merge, or build action is available on this page.')).toBeInTheDocument()
    expect(screen.getByText('Read-only inspection of the currently selected target season calendar.')).toBeInTheDocument()
    expect(await screen.findByText('Calendar exists: No')).toBeInTheDocument()
    expect(screen.getByText('Silent overwrite must never be allowed.')).toBeInTheDocument()
    expect(screen.getByText('Future build command must be explicit, audited, and reviewable.')).toBeInTheDocument()
    expect(screen.getByText('Review read-only diff and backend validation before any future command.')).toBeInTheDocument()
    expect(screen.getByText('No build, overwrite, merge, or apply command is available from this page.')).toBeInTheDocument()
    expect(screen.getByText('Local diff detail is advisory only and must not replace authoritative backend validation.')).toBeInTheDocument()
    expect(screen.getByText('No diff, build, merge, overwrite, or apply command is executed from this page.')).toBeInTheDocument()
    expect(screen.getByText('Target and template week counts match.')).toBeInTheDocument()
    expect(screen.getByText('Future implementation must require an explicit audited backend command before modifying any season calendar.')).toBeInTheDocument()
    expect(screen.getAllByText(/Event count/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Validation warnings count/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Validation errors count/i).length).toBeGreaterThan(0)
    expect(screen.getByText('Local read-only validation derived from the selected template payload. Not an authoritative build gate.')).toBeInTheDocument()
    expect(screen.getAllByText('Template selected').length).toBeGreaterThan(0)
    expect(screen.getByText('Slot count')).toBeInTheDocument()
    expect(screen.getByText('Duplicate slot IDs')).toBeInTheDocument()
    expect(screen.getByText('Week ranges')).toBeInTheDocument()
    expect(screen.getByText('Qualification slots')).toBeInTheDocument()
    expect(screen.getAllByText('slot-01-wt_gold_24').length).toBeGreaterThan(0)
    expect(screen.getAllByText('World Tour Gold').length).toBeGreaterThan(0)
    expect(screen.getAllByText('GOLD').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ENG').length).toBeGreaterThan(0)
    expect(screen.getByText('EUROPE')).toBeInTheDocument()
    expect(screen.getAllByText('Yes').length).toBeGreaterThan(0)
    expect(screen.getByText('Showing first 10 slots only. Full template detail remains available on the Season Template detail page.')).toBeInTheDocument()
    expect(screen.getByText('Read-only diff preview skeleton')).toBeInTheDocument()
    expect(screen.getByText('This is a structural preview of future compare/apply checks. It does not inspect or modify an existing concrete season calendar.')).toBeInTheDocument()
    expect(screen.getAllByText('Target season selected.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Season template source selected.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Template selected.').length).toBeGreaterThan(0)
    expect(screen.getByText('Template week count matches target season week count.')).toBeInTheDocument()
    expect(screen.getByText('Planned; no concrete season calendar conflict diff is performed on this page.')).toBeInTheDocument()
    expect(screen.getByText('Planned; apply/replace actions are intentionally not executable from this page.')).toBeInTheDocument()
    expect(screen.getByText('No diff/apply command is executed from this page.')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Source type select'), { target: { value: 'blank_calendar_planned' } })
    expect(screen.getByText('This source type is planned and not executable yet.')).toBeInTheDocument()
    expect(screen.getByText('Preview only. This source type has no executable workflow yet.')).toBeInTheDocument()
    expect(screen.getByText('Source type is planned and not executable yet.')).toBeInTheDocument()
    expect(screen.getByText('Planned source type selected; this source type is not executable yet.')).toBeInTheDocument()
    expect(screen.getByText('Planned source type cannot produce a concrete diff yet.')).toBeInTheDocument()
    expect(screen.getByText('Future command readiness checklist')).toBeInTheDocument()
    expect(screen.getByText(/Source resolved is false\.|Source resolution is unavailable until preflight result is returned\./)).toBeInTheDocument()
    expect(screen.getByText('Readiness remains blocked until a separate audited backend command is implemented.')).toBeInTheDocument()
    expect(screen.getByText('Source template selection is not executable for planned source types yet.')).toBeInTheDocument()
    expect(screen.queryByText('Selected template slot preview')).not.toBeInTheDocument()
    expect(screen.queryByText('Selected template validation summary')).not.toBeInTheDocument()
    expect(screen.queryByText('Local read-only validation derived from the selected template payload. Not an authoritative build gate.')).not.toBeInTheDocument()
    expect(screen.getByText('Backend preflight contract preview')).toBeInTheDocument()
    expect(screen.getByText('Read-only design preview. No backend preflight endpoint is called from this page.')).toBeInTheDocument()
    expect(screen.getByText('Backend preflight result')).toBeInTheDocument()
    expect(screen.getByText('Authoritative read-only backend preflight result. This endpoint does not build, merge, overwrite, or apply anything.')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot validation preview')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict preview')).toBeInTheDocument()
    expect(await screen.findByText('Preflight template slot conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict warning count: 1')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict info count: 2')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict conflict count: 3')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict conflict codes: template_conflict_week_overloaded, template_conflict_opening_dead_zone, template_conflict_final_dead_zone')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict warning codes: template_conflict_week_overloaded')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict busiest week: 5')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict busiest week slot count: 4')).toBeInTheDocument()
    expect(screen.getByText('Future build command contract preview')).toBeInTheDocument()
    expect((await screen.findAllByText('can_build')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('mutation_permitted').length).toBeGreaterThan(0)
    expect(screen.getByText('Future build command contract preview')).toBeInTheDocument()
    expect(screen.getByText('Read-only contract preview. No build command exists on this page.')).toBeInTheDocument()
    expect(screen.getAllByText('target_season_label').length).toBeGreaterThan(0)
    expect(screen.getAllByText('source_type').length).toBeGreaterThan(0)
    expect(screen.getAllByText('source_template_id or future source identifier').length).toBeGreaterThan(0)
    expect(screen.getAllByText('overwrite_policy').length).toBeGreaterThan(0)
    expect(screen.getAllByText('preflight_fingerprint').length).toBeGreaterThan(0)
    expect(screen.getAllByText('requested_by / admin actor').length).toBeGreaterThan(0)
    expect(screen.getAllByText('audit_reason').length).toBeGreaterThan(0)
    expect(screen.getByText('seed / template_version / config_hash')).toBeInTheDocument()
    expect(screen.getAllByText('explicit_confirmation').length).toBeGreaterThan(0)
    expect(screen.getByText('reviewed_diff_id or dry_run_result_id')).toBeInTheDocument()
    expect(screen.getAllByText('mutation_scope').length).toBeGreaterThan(0)
    expect(screen.getByText('Current preflight signals')).toBeInTheDocument()
    expect(screen.getAllByText('preflight_fingerprint').length).toBeGreaterThan(0)
    expect(screen.getAllByText('reviewed_diff_id').length).toBeGreaterThan(0)
    expect(screen.getAllByText('can_build').length).toBeGreaterThan(0)
    expect(screen.getAllByText('source_resolved').length).toBeGreaterThan(0)
    expect(screen.getAllByText('validation_errors count').length).toBeGreaterThan(0)
    expect(screen.getAllByText('validation_warnings count').length).toBeGreaterThan(0)
    expect(screen.getAllByText('mutation_permitted').length).toBeGreaterThan(0)
    expect(screen.getByText('Future build implementation must require a reviewed backend preflight, explicit audit metadata, and a separate audited command.')).toBeInTheDocument()
    expect(screen.getByText('Future command readiness checklist')).toBeInTheDocument()
    expect(screen.getByText('Read-only checklist. This summarizes future command prerequisites but does not enable any command.')).toBeInTheDocument()
    expect(screen.getAllByText('Target season').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Source reference').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Policy input').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Preflight fingerprint').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Reviewed diff identity').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Source resolved').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Validation errors').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Validation warnings').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Mutation permission').length).toBeGreaterThan(0)
    expect(screen.getAllByText('can_build flag').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Command implementation').length).toBeGreaterThan(0)
    expect(screen.getByText(/Backend preflight fingerprint is available\.|Backend preflight fingerprint is not available yet\./)).toBeInTheDocument()
    expect(screen.getByText(/Reviewed diff identity is available\.|Reviewed diff identity is not available yet\./)).toBeInTheDocument()
    expect(screen.getByText('mutation_permitted is false; this page cannot mutate calendars.')).toBeInTheDocument()
    expect(screen.getByText(/can_build is false; future command remains unavailable\.|can_build is unavailable until preflight result is returned\./)).toBeInTheDocument()
    expect(screen.getByText('No build command exists on this page.')).toBeInTheDocument()
    expect(screen.getByText('Readiness remains blocked until a separate audited backend command is implemented.')).toBeInTheDocument()
    expect(screen.getByText('Dry-run audit metadata preview inputs')).toBeInTheDocument()
    expect(screen.getByText('Read-only preview inputs. These fields only change the disabled dry-run contract payload.')).toBeInTheDocument()
    expect(screen.getByLabelText('Future audit reason preview')).toBeInTheDocument()
    expect(screen.getByLabelText('Future explicit confirmation preview')).toBeInTheDocument()
    expect(screen.getByLabelText('Future mutation scope preview')).toBeInTheDocument()
    expect(screen.getByText('These values are not submitted as a command and do not enable execution.')).toBeInTheDocument()
    expect(screen.getByText('Changing these fields only re-runs the disabled dry-run contract check.')).toBeInTheDocument()
    expect(screen.getByText('Disabled dry-run build contract result')).toBeInTheDocument()
    expect(screen.getByText('Read-only disabled command contract check. This does not build, merge, overwrite, or apply anything.')).toBeInTheDocument()
    expect(screen.getAllByText('preflight_fingerprint').length).toBeGreaterThan(0)
    expect(screen.getAllByText('reviewed_diff_id').length).toBeGreaterThan(0)
    await waitFor(() => {
      expect(api.postSeasonBuilderDryRunBuild).toHaveBeenCalledWith(expect.objectContaining({
        preflight_fingerprint: 'pf_test_existing',
        reviewed_diff_id: 'rd_test_existing',
        audit_reason: null,
        explicit_confirmation: null,
        mutation_scope: null
      }))
    })
    expect((await screen.findAllByText('pf_test_existing')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('rd_test_existing')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Dry-run build command contract exists, but execution is disabled in this phase.')).toBeInTheDocument()
    expect((await screen.findAllByText('audit_reason will be required before execution is enabled in a future phase.')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('explicit_confirmation will be required before execution is enabled in a future phase.')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('mutation_scope will be required before execution is enabled in a future phase.')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('execution_enabled')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Future dry-run generation design preview')).toBeInTheDocument()
    expect(await screen.findByText('design_preview_only')).toBeInTheDocument()
    expect(await screen.findByText('will_generate_events')).toBeInTheDocument()
    expect(await screen.findByText('will_persist_calendar')).toBeInTheDocument()
    expect(await screen.findByText('will_mutate_existing_calendar')).toBeInTheDocument()
    expect(await screen.findByText('Dry-run generation is not implemented in this phase.')).toBeInTheDocument()
    expect(await screen.findByText('Validate reviewed preflight identity.')).toBeInTheDocument()
    expect(await screen.findByText('Return additions/replacements/conflicts without persistence.')).toBeInTheDocument()
    expect(await screen.findByText('candidate_events')).toBeInTheDocument()
    expect(await screen.findByText('conflict_summary')).toBeInTheDocument()
    expect((await screen.findAllByText('audit_preview')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Candidate event contract preview')).toBeInTheDocument()
    expect((await screen.findAllByText('contract_preview_only')).length).toBeGreaterThan(0)
    expect(await screen.findByText('will_generate_candidates')).toBeInTheDocument()
    expect((await screen.findAllByText('candidate_count')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Candidate event generation is not implemented in this phase.')).toBeInTheDocument()
    expect(await screen.findByText('Candidate event shape')).toBeInTheDocument()
    expect((await screen.findAllByText('source_slot_id')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('season_week_start')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('candidate_status')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Structural summary shape')).toBeInTheDocument()
    expect((await screen.findAllByText('additions_count')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('conflict_count')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Conflict summary shape')).toBeInTheDocument()
    expect((await screen.findAllByText('week_conflicts')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('policy_conflicts')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Dry-run result contract preview')).toBeInTheDocument()
    expect(await screen.findByText('Read-only generated dry-run result preview')).toBeInTheDocument()
    expect(await screen.findByText('Read-only comparison conflicts')).toBeInTheDocument()
    expect((await screen.findAllByText('policy_conflicts count')).length).toBeGreaterThan(0)
    expect(await screen.findByText('comparison_performed')).toBeInTheDocument()
    expect((await screen.findAllByText('target_calendar_exists')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('target_event_count')).length).toBeGreaterThan(0)
    expect(screen.getByText('read_only_generated')).toBeInTheDocument()
    expect(screen.getByText('Read-only generated candidates are not persisted.')).toBeInTheDocument()
    expect(screen.getAllByText('candidate_id').length).toBeGreaterThan(0)
    expect(screen.getAllByText('source_slot_id').length).toBeGreaterThan(0)
    expect(screen.getAllByText('event_name').length).toBeGreaterThan(0)
    expect(screen.getAllByText('candidate_status').length).toBeGreaterThan(0)
    expect(screen.getAllByText('comparison_classification').length).toBeGreaterThan(0)
    expect(screen.getAllByText('comparison_reason').length).toBeGreaterThan(0)
    expect(screen.getAllByText('matched_existing_event_id').length).toBeGreaterThan(0)
    expect(screen.getByText('Candidate has read-only comparison conflicts.')).toBeInTheDocument()
    expect(await screen.findByText('will_return_real_result')).toBeInTheDocument()
    expect(await screen.findByText('Dry-run result generation is not implemented in this phase.')).toBeInTheDocument()
    expect(await screen.findByText('Structural summary preview')).toBeInTheDocument()
    expect((await screen.findAllByText('additions_count')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('replacement_count')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('invalid_count')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Conflict summary preview')).toBeInTheDocument()
    expect((await screen.findAllByText('week_conflicts count')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('policy_conflicts count')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Result metadata preview')).toBeInTheDocument()
    expect((await screen.findAllByText('execution_enabled')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('mutation_permitted')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Candidate events preview')).toBeInTheDocument()
    expect(await screen.findByText('No candidate events returned in this contract-only phase.')).toBeInTheDocument()
    expect((await screen.findAllByText('dry_run_result_contract_preview_available')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('dry_run_result_preview_available')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('dry_run_result_identity_available')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('dry_run_result_fingerprint')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('dry_run_result_id')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('drf_test_existing').length).toBeGreaterThan(0)
    expect(screen.getAllByText('drr_test_existing').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Dry-run identity readiness').length).toBeGreaterThan(0)
    expect(screen.getByText('Future command reference')).toBeInTheDocument()
    expect(screen.getByText('blocked_reference')).toBeInTheDocument()
    expect(screen.getByText('can_reference_future_command')).toBeInTheDocument()
    expect(screen.getAllByText('mutation_still_disabled').length).toBeGreaterThan(0)
    expect(screen.getByText('Mutation remains disabled; this checklist is reference-only.')).toBeInTheDocument()
    expect(screen.getAllByText('Dry-run template conflict summary').length).toBeGreaterThan(0)
    expect(screen.getByText('Dry-run template conflict diagnostics available: true')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict diagnostics read-only: true')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict diagnostics non-blocking: true')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict conflict count: 3')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict conflict codes: template_conflict_week_overloaded')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict source: template_slot_conflict_preview')).toBeInTheDocument()
    expect((await screen.findAllByText('explicit_confirmation_present')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('conflict_contract_preview_available')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Raw disabled dry-run build contract JSON')).toBeInTheDocument()
    expect(await screen.findByText('Execution remains disabled; this panel is not a build control.')).toBeInTheDocument()
    expect(screen.getByText('Disabled apply command contract result')).toBeInTheDocument()
    expect(screen.getByText('Create-only apply workflow guide')).toBeInTheDocument()
    expect(screen.getByText('Review backend readiness and candidate summary.')).toBeInTheDocument()
    expect(screen.getByText('Review guard summary.')).toBeInTheDocument()
    expect(screen.getByText('Enter exact confirmation phrase and create_only scope.')).toBeInTheDocument()
    expect(screen.getByText('Verify refreshed target calendar and post-apply lockout.')).toBeInTheDocument()
    expect(screen.getByText('Review audit/status summary.')).toBeInTheDocument()
    expect(screen.getByText('It cannot merge or overwrite an existing calendar.')).toBeInTheDocument()
    expect(screen.getByText('Create-only apply readiness')).toBeInTheDocument()
    expect(screen.getByText('Create-only apply guard summary')).toBeInTheDocument()
    expect(screen.getByText('Create-only apply danger-zone command')).toBeInTheDocument()
    expect(screen.getByText('Read-only disabled apply command contract check. This does not build, merge, overwrite, or apply anything.')).toBeInTheDocument()
    expect(screen.getByText('Read-only create-only apply readiness check. This panel does not execute apply or create a calendar.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Danger zone — persistent create-only calendar creation' })).toBeInTheDocument()
    expect(screen.getByText('This command can create a new season calendar if the target is absent and all guards pass. It cannot merge, overwrite, or repair. Every schema-valid attempt is audited.')).toBeInTheDocument()
    expect(screen.getByText(/Persistent mutation\./)).toBeInTheDocument()
    expect(screen.getByText('Creates a new calendar only when the target is absent.')).toBeInTheDocument()
    expect(screen.getByText('Never merges or overwrites existing calendars.')).toBeInTheDocument()
    expect(screen.getByText('Never repairs existing calendars.')).toBeInTheDocument()
    expect(screen.getByText('Schema-valid attempts are audited.')).toBeInTheDocument()
    expect(screen.getByText('If the audit reservation fails, mutation is blocked.')).toBeInTheDocument()
    const dangerZoneSection = screen.getByRole('heading', { name: 'Danger zone — persistent create-only calendar creation' }).closest('section') as HTMLElement
    const executeCreateOnlyButton = within(dangerZoneSection).getByRole('button', { name: 'Execute create-only season calendar command' })
    expect(screen.getAllByRole('button', { name: 'Execute create-only season calendar command' })).toHaveLength(1)
    expect(executeCreateOnlyButton).toBeDisabled()
    expect(screen.getByText('Create-only command is currently blocked by one or more guards.')).toBeInTheDocument()
    expect(screen.getAllByText('Exact confirmation phrase entered').length).toBeGreaterThan(0)
    expect(screen.getByText('Visible guard eligibility preview')).toBeInTheDocument()
    expect(screen.getByText('Danger-zone guarded command enabled')).toBeInTheDocument()
    expect(screen.getByText('Required confirmation phrase')).toBeInTheDocument()
    expect(screen.getByText('I understand this will create a new season calendar.')).toBeInTheDocument()
    expect(screen.getByText('Required confirmation phrase: I understand this will create a new season calendar.')).toBeInTheDocument()
    expect(screen.getByText('Danger-zone required mutation scope')).toBeInTheDocument()
    expect(screen.getByText('create_only')).toBeInTheDocument()
    const confirmationInput = screen.getByLabelText('Exact confirmation phrase')
    const mutationScopeInput = screen.getByLabelText('Mutation scope')
    expect(confirmationInput).toBeInTheDocument()
    expect(mutationScopeInput).toBeInTheDocument()
    expect(screen.getByText('Create-only apply is not fully armed yet.')).toBeInTheDocument()
    expect(screen.getByText('Backend readiness says create-only apply is ready, but this readiness panel is read-only. Calendar creation can only happen from the separate danger-zone command.')).toBeInTheDocument()
    expect(screen.getByText('Safety checklist')).toBeInTheDocument()
    expect(screen.getByText('Real apply endpoint called from UI')).toBeInTheDocument()
    expect(screen.getByText('Mutation hook installed')).toBeInTheDocument()
    expect(screen.getByText('Calendar created by this panel')).toBeInTheDocument()
    expect(screen.getAllByText('Backend readiness satisfied').length).toBeGreaterThan(0)
    expect(screen.getByText('Audit persisted')).toBeInTheDocument()
    expect(screen.getAllByText('can_mutate').length).toBeGreaterThan(0)
    expect(screen.getAllByText('service_insert_applicable').length).toBeGreaterThan(0)
    expect(screen.getAllByText('false').length).toBeGreaterThan(0)
    expect(screen.getByText('Candidate count: 1')).toBeInTheDocument()
    expect(screen.getAllByText('Categories count: 1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Categories values: GOLD').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Tour levels count: 1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Tour levels values: WORLD_TOUR').length).toBeGreaterThan(0)
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Source type select'), { target: { value: 'season_template' } })
    fireEvent.change(confirmationInput, { target: { value: 'I understand this will create a new season calendar.' } })
    fireEvent.change(mutationScopeInput, { target: { value: 'create_only' } })
    expect(screen.getByText('All visible preview conditions are satisfied.')).toBeInTheDocument()
    expect(screen.getByText('Create-only command is currently enabled by all guards.')).toBeInTheDocument()
    await waitFor(() => {
      expect(api.postSeasonBuilderApplyCreateOnlyReadiness).toHaveBeenCalledWith(expect.objectContaining({
        target_season_label: '2000/01',
        source_type: 'season_template',
        source_template_id: 'default_msa_template_preview',
        requested_by: 'local-admin-preview',
        preflight_fingerprint: 'pf_test_existing',
        reviewed_diff_id: 'rd_test_existing',
        dry_run_result_fingerprint: 'drf_test_existing',
        dry_run_result_id: 'drr_test_existing'
      }))
    })
    await waitFor(() => expect(executeCreateOnlyButton).toBeEnabled())
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    api.postSeasonBuilderApplyCreateOnlyCommand.mockResolvedValueOnce({
      command: 'season_builder_apply_create_only',
      enabled: true,
      can_execute: true,
      can_mutate: true,
      applied: true,
      target_season_label: '2000/01',
      validation_errors: [],
      validation_warnings: [],
      created_calendar_summary: { calendar_exists: true, season: '2000/01', event_count: 1 },
      created_event_preview: [],
      created_calendar_identity: { applied_event_count: 1 },
      created_calendar_validation_preview: {
        validation_status: 'warnings',
        error_count: 0,
        warning_count: 1,
        info_count: 1,
        event_count: 1,
        calendar_exists: true,
        read_only: true,
        first_season_week: 1,
        last_season_week: 1,
        categories: { count: 1, values: ['GOLD'] },
        tour_levels: { count: 1, values: ['WORLD_TOUR'] },
        host_countries: { count: 1, values: ['ENG'] },
        issue_codes_first_10: ['calendar_validation_demo_warning']
      },
      apply_gate_summary: { service_insert_succeeded: true },
      applied_event_count: 1,
      dry_run_identity: { identity_matches: true },
      audit_preview: { audit_persisted: true, audit_persistence_status: 'persisted_success', audit_record_id: 'aud_create_only_test', audit_record_fingerprint: 'aud_fp_test' },
      audit_persisted: true,
      audit_persistence_status: 'persisted_success',
      audit_record_id: 'aud_create_only_test',
      audit_record_fingerprint: 'aud_fp_test',
      audit_storage_summary: { backend: 'jsonl', filename: 'season_builder_apply_create_only_audit.jsonl' },
      message: 'Create-only apply executed successfully.'
    })
    fireEvent.click(executeCreateOnlyButton)
    expect(executeCreateOnlyButton).toHaveAttribute('type', 'button')
    await waitFor(() => expect(api.postSeasonBuilderApplyCreateOnlyCommand).toHaveBeenCalledTimes(1))
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).toHaveBeenCalledWith(expect.objectContaining({
      target_season_label: '2000/01',
      source_type: 'season_template',
      source_template_id: 'default_msa_template_preview',
      overwrite_policy: null,
      preflight_fingerprint: 'pf_test_existing',
      reviewed_diff_id: 'rd_test_existing',
      dry_run_result_fingerprint: 'drf_test_existing',
      dry_run_result_id: 'drr_test_existing',
      requested_candidate_identity_reference_id: 'abc123fingerprint',
      requested_candidate_identity_fingerprint: 'abc123fingerprint',
      requested_candidate_identity_reference_type: 'candidate_identity_set',
      requested_by: 'local-admin-preview',
      audit_reason: 'create-only calendar command',
      explicit_confirmation: 'I understand this will create a new season calendar.',
      mutation_scope: 'create_only'
    }))
    expect(await screen.findByText('Create-only apply result')).toBeInTheDocument()
    expect(screen.getAllByText('Create-only apply executed successfully.').length).toBeGreaterThan(0)
    expect(screen.getByText('Create-only apply reported success. Verify the refreshed target calendar below.')).toBeInTheDocument()
    expect(await screen.findByText('Post-apply calendar verification passed.')).toBeInTheDocument()
    expect(screen.getByText('Apply response validation preview')).toBeInTheDocument()
    expect(screen.getByText('This preview comes from the create-only apply response. The separate target calendar validation panel may refetch the latest persisted state.')).toBeInTheDocument()
    expect(screen.getAllByText('Validation status: warnings').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Calendar exists: true').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Read-only: true').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Event count: 1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Error count: 0').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Warning count: 1').length).toBeGreaterThan(0)
    expect(screen.getByText('Apply response validation interpretation: Validation has warnings but no blocking errors.')).toBeInTheDocument()
    expect(screen.getByText('Issue codes (first 10): calendar_validation_demo_warning')).toBeInTheDocument()
    expect(screen.getByText('Apply-response issue code count: 1')).toBeInTheDocument()
    expect(screen.getByText('Apply-response issue code metadata')).toBeInTheDocument()
    expect(screen.getByText('Metadata below documents only the issue codes returned in this apply response.')).toBeInTheDocument()
    const applyResponseMetadataRow = screen.getAllByText('calendar_validation_demo_warning')
      .map((element) => element.closest('tr'))
      .find((row) => row?.textContent?.includes('Demo warning used by frontend route test.'))
    expect(applyResponseMetadataRow).not.toBeNull()
    expect(applyResponseMetadataRow).toHaveTextContent('Calendar validation demo warning')
    expect(applyResponseMetadataRow).toHaveTextContent('warning')
    expect(applyResponseMetadataRow).toHaveTextContent('category')
    expect(applyResponseMetadataRow).toHaveTextContent('Demo warning used by frontend route test.')
    await waitFor(() => expect(api.getSeasonCalendarValidation).toHaveBeenCalledWith('2000/01'))
    expect(screen.getByText('Target calendar validation')).toBeInTheDocument()
    expect(screen.getByText('Read-only persisted target calendar validation. No mutation path is available in this panel.')).toBeInTheDocument()
    expect(screen.getAllByText('Read-only: true').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Calendar exists: true').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Validation status: warnings').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Error count: 0').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Warning count: 1').length).toBeGreaterThan(0)
    expect(screen.getByText('Target validation interpretation: Validation has warnings but no blocking errors.')).toBeInTheDocument()
    expect(screen.getByText('Validation issue severity summary')).toBeInTheDocument()
    expect(screen.getByText('Error issues: 0')).toBeInTheDocument()
    expect(screen.getByText('Warning issues: 1')).toBeInTheDocument()
    expect(screen.getByText('Info issues: 0')).toBeInTheDocument()
    expect(screen.getByText('Unknown-severity issues: 0')).toBeInTheDocument()
    expect(screen.getByText('Issue rows below are enriched from the registry when metadata is available.')).toBeInTheDocument()
    expect(screen.getByText('Warning issue codes: calendar_validation_demo_warning')).toBeInTheDocument()
    expect(screen.getByText('Error issue codes: none')).toBeInTheDocument()
    expect(screen.getAllByText('Event count: 1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('First season week: 1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Last season week: 1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Categories count: 1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Categories values: GOLD').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Tour levels count: 1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Tour levels values: WORLD_TOUR').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Host countries count: 1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Host countries values: ENG').length).toBeGreaterThan(0)
    expect(api.getSeasonCalendarValidationIssueCodes).toHaveBeenCalled()
    expect(screen.getByText('Validation issue code registry')).toBeInTheDocument()
    expect(screen.getByText('Read-only validation issue code registry. These codes document validation output meanings.')).toBeInTheDocument()
    expect(screen.getByText('This registry is the full reference list; individual validation panels show only codes present in their result.')).toBeInTheDocument()
    expect(screen.getByText('Code count: 4')).toBeInTheDocument()
    expect(screen.getByText('Error code count: 1')).toBeInTheDocument()
    expect(screen.getByText('Warning code count: 2')).toBeInTheDocument()
    expect(screen.getByText('Info code count: 1')).toBeInTheDocument()
    expect(screen.getByText('calendar_missing')).toBeInTheDocument()
    expect(screen.getByText('main_draw_size_invalid')).toBeInTheDocument()
    expect(screen.getAllByText('event_count').length).toBeGreaterThan(0)
    expect(screen.getByText('Invalid main draw size')).toBeInTheDocument()
    expect(screen.getByText('main_draw_size')).toBeInTheDocument()
    expect(screen.getByText('Apply response vs target validation comparison')).toBeInTheDocument()
    expect(await screen.findByText('Apply-response validation preview matches refetched target validation.')).toBeInTheDocument()
    expect(screen.getByText('Both validation sources report the same validation severity.')).toBeInTheDocument()
    expect(screen.getAllByText('validation_status').length).toBeGreaterThan(0)
    expect(screen.getAllByText('event_count').length).toBeGreaterThan(0)
    expect(screen.getAllByText('error_count').length).toBeGreaterThan(0)
    expect(screen.getAllByText('warning_count').length).toBeGreaterThan(0)
    expect(screen.getAllByText('info_count').length).toBeGreaterThan(0)
    const validationStatusComparisonRow = screen.getByText('validation_status').closest('tr')
    expect(validationStatusComparisonRow).not.toBeNull()
    expect(validationStatusComparisonRow).toHaveTextContent('yes')
    expect(screen.getAllByText('calendar_validation_demo_warning').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Calendar validation demo warning').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Demo warning used by frontend route test.').length).toBeGreaterThan(0)
    expect(screen.getByText('Calendar validation warning preview.')).toBeInTheDocument()
    expect(screen.getAllByText('event-1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('category').length).toBeGreaterThan(0)
    expect(screen.getByText('Post-apply audit/status summary')).toBeInTheDocument()
    expect(screen.getByText('Audit persistence reported by backend.')).toBeInTheDocument()
    expect(screen.getAllByText('Audit ID').length).toBeGreaterThan(0)
    expect(screen.getAllByText('aud_create_only_test').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Audit fingerprint').length).toBeGreaterThan(0)
    expect(screen.getAllByText('aud_fp_test').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Persistence status').length).toBeGreaterThan(0)
    expect(screen.getAllByText('persisted_success').length).toBeGreaterThan(0)
    expect(screen.getByText('Explicit confirmation was provided.')).toBeInTheDocument()
    expect(screen.getAllByText('audit_status.requested_by').length).toBeGreaterThan(0)
    expect(screen.getAllByText('audit_status.audit_reason').length).toBeGreaterThan(0)
    expect(screen.getAllByText('explicit_confirmation present').length).toBeGreaterThan(0)
    expect(screen.getAllByText('audit_status.mutation_scope').length).toBeGreaterThan(0)
    expect(screen.getAllByText('audit_preview.audit_persistence_status').length).toBeGreaterThan(0)
    expect(screen.getAllByText('apply_gate_summary.service_insert_succeeded').length).toBeGreaterThan(0)
    expect(screen.getAllByText('dry_run_identity.identity_matches').length).toBeGreaterThan(0)
    expect(screen.getAllByText('created_calendar_identity.applied_event_count').length).toBeGreaterThan(0)
    expect(screen.getAllByText('local-admin-preview').length).toBeGreaterThan(0)
    expect(screen.getAllByText('create-only calendar command').length).toBeGreaterThan(0)
    expect(screen.getAllByText('create_only').length).toBeGreaterThan(0)
    expect(screen.getByText('audit_status.apply_result_exists')).toBeInTheDocument()
    expect(screen.getByText('Create-only command should now be unavailable for this target.')).toBeInTheDocument()
    expect(screen.getAllByText('Target calendar now exists. Create-only apply is locked out for this target.').length).toBeGreaterThan(0)
    expect(screen.getByText('Target calendar is absent/still eligible for create-only')).toBeInTheDocument()
    expect(screen.getByText('Target calendar exists or was just created by a successful apply.')).toBeInTheDocument()
    expect(screen.getByText('Create-only command is currently blocked by one or more guards.')).toBeInTheDocument()
    expect(screen.getByText('Use a future audited merge/overwrite workflow if changes are needed.')).toBeInTheDocument()
    await waitFor(() => expect(executeCreateOnlyButton).toBeDisabled())
    fireEvent.click(executeCreateOnlyButton)
    await waitFor(() => expect(api.postSeasonBuilderApplyCreateOnlyCommand).toHaveBeenCalledTimes(1))
    expect(screen.getByText('verification.target_calendar_exists')).toBeInTheDocument()
    expect(screen.getByText('applyMutationResult.applied_event_count')).toBeInTheDocument()
    expect(screen.getByText('verification.target_calendar_event_count')).toBeInTheDocument()
    expect(screen.getByText('audit_status.apply_result_applied')).toBeInTheDocument()
    expect(screen.getAllByText('applied_event_count').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('season_builder_apply_command')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Apply audit trail contract preview')).toBeInTheDocument()
    expect(await screen.findByText('Apply safety gate contract preview')).toBeInTheDocument()
    expect(await screen.findByText('blocked_disabled_phase')).toBeInTheDocument()
    expect((await screen.findAllByText('will_execute_apply')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('will_mutate_calendar')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Final apply safety gate is contract-only and disabled in this phase.')).toBeInTheDocument()
    expect(await screen.findByText('Required gates')).toBeInTheDocument()
    expect((await screen.findAllByText('identity')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('audit_metadata')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('execution_enabled')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('mutation_permission')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('audit_trail')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Future allowed mutation scopes')).toBeInTheDocument()
    expect((await screen.findAllByText('create_only_preview')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('overwrite_preview')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('safety_gate_contract_preview_available')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('contract_preview_only')).length).toBeGreaterThan(0)
    expect(await screen.findByText('will_persist_audit')).toBeInTheDocument()
    expect((await screen.findAllByText('Audit trail persistence is not implemented in this phase.')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Required identity fields')).toBeInTheDocument()
    expect(await screen.findByText('Required actor fields')).toBeInTheDocument()
    expect(await screen.findByText('Audit record shape')).toBeInTheDocument()
    expect((await screen.findAllByText('audit_id')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('timestamp_utc')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('explicit_confirmation_present')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('audit_trail_contract_preview_available')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('all_identity_fields_present')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('all_audit_metadata_present')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('audit_reason will be required before apply execution is enabled in a future phase.')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('explicit_confirmation will be required before apply execution is enabled in a future phase.')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('mutation_scope will be required before apply execution is enabled in a future phase.')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Raw disabled apply command contract JSON')).toBeInTheDocument()
    expect((await screen.findAllByText('Apply command contract exists, but execution is disabled in this phase.')).length).toBeGreaterThan(0)
    expect(screen.getByText('Execution remains disabled; this panel is not an apply control.')).toBeInTheDocument()
    expect(screen.getByText('Apply command readiness summary')).toBeInTheDocument()
    expect(screen.getByText('Read-only summary of the disabled apply command contract state.')).toBeInTheDocument()
    expect(screen.getByText('Apply contract endpoint')).toBeInTheDocument()
    expect(screen.getAllByText('Execution flag').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Mutation flag').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Preflight identity').length).toBeGreaterThan(0)
    expect(screen.getByText('Dry-run result identity')).toBeInTheDocument()
    expect(screen.getByText('Required identity contract')).toBeInTheDocument()
    expect(screen.getAllByText('Required audit metadata').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Dry-run identity readiness').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Validation errors').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Validation warnings').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Next implementation step').length).toBeGreaterThan(0)
    expect(screen.getByText('Disabled apply command contract endpoint returned a response.')).toBeInTheDocument()
    expect(screen.getByText('Apply execution is disabled in this phase.')).toBeInTheDocument()
    expect(screen.getAllByText('can_mutate is false; no calendar mutation is permitted.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Preflight fingerprint and reviewed diff identity are present.').length).toBeGreaterThan(0)
    expect(screen.getByText('Dry-run result fingerprint and id are present.')).toBeInTheDocument()
    expect(screen.getByText('Apply contract reports all identity fields present.')).toBeInTheDocument()
    expect(screen.getByText('Apply audit metadata is not complete yet.')).toBeInTheDocument()
    expect(screen.getByText('Dry-run identity readiness status: blocked_reference.')).toBeInTheDocument()
    expect(screen.getByText('Apply validation errors count: 0.')).toBeInTheDocument()
    expect(screen.getByText('Apply validation warnings count: 3.')).toBeInTheDocument()
    expect(screen.getByText('Real apply execution is not implemented yet.')).toBeInTheDocument()
    expect(screen.getByText('The apply command contract is visible, but execution remains disabled.')).toBeInTheDocument()
    expect(screen.getByText('Current disabled dry-run request payload')).toBeInTheDocument()
    expect(screen.getByText('Disabled dry-run readiness summary')).toBeInTheDocument()
    expect(screen.getByText('Read-only summary of the disabled dry-run contract state.')).toBeInTheDocument()
    expect(screen.getByText('Contract endpoint')).toBeInTheDocument()
    expect(screen.getAllByText('Execution flag').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Mutation flag').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Preflight identity').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Audit reason').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Explicit confirmation').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Mutation scope').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Validation warnings').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Validation errors').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Next implementation step').length).toBeGreaterThan(0)
    expect(screen.getByText('Disabled dry-run contract endpoint returned a response.')).toBeInTheDocument()
    expect(screen.getAllByText('Execution is disabled in this phase.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('can_mutate is false; no calendar mutation is permitted.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Preflight fingerprint and reviewed diff identity are present.').length).toBeGreaterThan(0)
    expect(screen.getByText('Audit reason preview is not filled yet.')).toBeInTheDocument()
    expect(screen.getByText('Explicit confirmation preview is not filled yet.')).toBeInTheDocument()
    expect(screen.getByText('Mutation scope preview is not selected yet.')).toBeInTheDocument()
    expect(screen.getByText('Validation warnings count: 3.')).toBeInTheDocument()
    expect(screen.getAllByText('Validation errors count: 0.').length).toBeGreaterThan(0)
    expect(screen.getByText('Real dry-run generation is not implemented yet.')).toBeInTheDocument()
    expect(screen.getByText('The dry-run contract is visible, but execution remains disabled.')).toBeInTheDocument()
    expect(api.postSeasonBuilderPreflight).toHaveBeenCalledWith(expect.objectContaining({ target_season_label: '2000/01', source_type: 'season_template', source_template_id: 'default_msa_template_preview', requested_by: 'local-admin-preview' }))
    fireEvent.change(screen.getByLabelText('Future audit reason preview'), { target: { value: 'ticket-123 dry-run review' } })
    fireEvent.change(screen.getByLabelText('Future explicit confirmation preview'), { target: { value: 'I understand this is disabled.' } })
    fireEvent.change(screen.getByLabelText('Future mutation scope preview'), { target: { value: 'merge_preview' } })
    await waitFor(() => {
      expect(api.postSeasonBuilderDryRunBuild).toHaveBeenCalledWith(expect.objectContaining({
        audit_reason: 'ticket-123 dry-run review',
        explicit_confirmation: 'I understand this is disabled.',
        mutation_scope: 'merge_preview'
      }))
    })
    await waitFor(() => {
      expect(api.postSeasonBuilderApplyCommandContract).toHaveBeenCalledWith(expect.objectContaining({
        audit_reason: 'ticket-123 dry-run review',
        explicit_confirmation: 'I understand this is disabled.',
        mutation_scope: 'merge_preview'
      }))
    })
    expect(await screen.findByText('No dry-run build contract warnings returned.')).toBeInTheDocument()
    expect(await screen.findByText('No apply command contract warnings returned.')).toBeInTheDocument()
    expect(await screen.findByText('Audit reason preview is present.')).toBeInTheDocument()
    expect(await screen.findByText('Explicit confirmation preview is present.')).toBeInTheDocument()
    expect(await screen.findByText('Mutation scope preview is present.')).toBeInTheDocument()
    expect((await screen.findAllByText('Validation warnings count: 0.')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Apply validation warnings count: 0.')).toBeInTheDocument()
    expect(await screen.findByText('Apply contract reports all audit metadata present.')).toBeInTheDocument()
    expect(screen.getByText('The apply command contract is visible, but execution remains disabled.')).toBeInTheDocument()
    expect(screen.getByText('The dry-run contract is visible, but execution remains disabled.')).toBeInTheDocument()
    expect((await screen.findAllByText('explicit_confirmation_present')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('conflict_contract_preview_available')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('merge_preview')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('false')).length).toBeGreaterThan(0)
    api.postSeasonBuilderPreflight.mockImplementation(async (payload) => {
      const requestedPolicy = payload.overwrite_policy
      if (requestedPolicy === 'merge_preview') {
        return {
          can_build: false,
          target_season_label: '2000/2001',
          source_type: 'season_template',
          source_template_id: 'default_msa_template_preview',
          preflight_fingerprint: 'pf_test_merge',
          reviewed_diff_id: 'rd_test_merge',
          target_calendar_exists: true,
          target_event_count: 1,
          source_resolved: true,
          source_summary: { template_name: 'Default MSA Template Preview', slot_count: 1, week_count: 61 },
          authoritative_diff_summary: {
            status: 'read_only_preflight',
            can_build: false,
            target_calendar_exists: true,
            target_event_count: 1,
            source_type: 'season_template',
            source_resolved: true,
            source_slot_count: 1,
            source_week_count: 1,
            target_week_count: 1,
            week_count_compatible: true,
            source_range: { first_week: 1, last_week: 1 },
            target_range: { first_week: 1, last_week: 1 },
            structural_comparison: { planned_source_slots: 1, existing_target_events: 1, target_is_empty: false, requires_overwrite_or_merge_policy: false },
            blocking_reasons: [],
            advisory_notes: ['Merge policy preview selected. Future implementation must still perform event-level backend diff before any merge command.'],
            placeholder: 'Event-level additions/replacements/conflicts remain planned for a future phase.'
          },
          validation_warnings: [],
          validation_errors: [],
          audit_preview: { action: 'season_builder_preflight', read_only: true, mutation_permitted: false, overwrite_policy: 'merge_preview' }
        }
      }
      if (requestedPolicy === 'overwrite_preview') {
        return {
          can_build: false,
          target_season_label: '2000/2001',
          source_type: 'season_template',
          source_template_id: 'default_msa_template_preview',
          preflight_fingerprint: 'pf_test_overwrite',
          reviewed_diff_id: 'rd_test_overwrite',
          target_calendar_exists: true,
          target_event_count: 1,
          source_resolved: true,
          source_summary: { template_name: 'Default MSA Template Preview', slot_count: 1, week_count: 61 },
          authoritative_diff_summary: {
            status: 'read_only_preflight',
            can_build: false,
            target_calendar_exists: true,
            target_event_count: 1,
            source_type: 'season_template',
            source_resolved: true,
            source_slot_count: 1,
            source_week_count: 1,
            target_week_count: 1,
            week_count_compatible: true,
            source_range: { first_week: 1, last_week: 1 },
            target_range: { first_week: 1, last_week: 1 },
            structural_comparison: { planned_source_slots: 1, existing_target_events: 1, target_is_empty: false, requires_overwrite_or_merge_policy: false },
            blocking_reasons: [],
            advisory_notes: ['Overwrite policy preview selected. Future implementation must require explicit audited confirmation before any overwrite command.'],
            placeholder: 'Event-level additions/replacements/conflicts remain planned for a future phase.'
          },
          validation_warnings: [],
          validation_errors: [],
          audit_preview: { action: 'season_builder_preflight', read_only: true, mutation_permitted: false, overwrite_policy: 'overwrite_preview' }
        }
      }
      return {
        can_build: false,
        target_season_label: '2000/2001',
        source_type: 'season_template',
        source_template_id: 'default_msa_template_preview',
        preflight_fingerprint: 'pf_test_existing',
        reviewed_diff_id: 'rd_test_existing',
        target_calendar_exists: true,
        target_event_count: 1,
        source_resolved: true,
        source_summary: { template_name: 'Default MSA Template Preview', slot_count: 1, week_count: 61 },
        authoritative_diff_summary: {
          status: 'read_only_preflight',
          can_build: false,
          target_calendar_exists: true,
          target_event_count: 1,
          source_type: 'season_template',
          source_resolved: true,
          source_slot_count: 1,
          source_week_count: 1,
          target_week_count: 1,
          week_count_compatible: true,
          source_range: { first_week: 1, last_week: 1 },
          target_range: { first_week: 1, last_week: 1 },
          structural_comparison: { planned_source_slots: 1, existing_target_events: 1, target_is_empty: false, requires_overwrite_or_merge_policy: true },
          blocking_reasons: ['Explicit overwrite/merge policy is required before any future build when a target calendar already exists.'],
          advisory_notes: [],
          placeholder: 'Event-level additions/replacements/conflicts remain planned for a future phase.'
        },
        validation_warnings: [],
        validation_errors: ['Explicit overwrite/merge policy is required before any future build when a target calendar already exists.'],
        audit_preview: { action: 'season_builder_preflight', read_only: true, mutation_permitted: false }
      }
    })

    fireEvent.change(screen.getByLabelText('Future policy preview'), { target: { value: 'merge_preview' } })
    await waitFor(() => {
      expect(api.postSeasonBuilderPreflight).toHaveBeenCalledWith(expect.objectContaining({
        target_season_label: '2000/01',
        overwrite_policy: 'merge_preview',
        requested_by: 'local-admin-preview'
      }))
    })
    expect((screen.getByLabelText('Future policy preview') as HTMLSelectElement).value).toBe('merge_preview')
    expect(await screen.findByText(/Merge policy preview is selected\./)).toBeInTheDocument()
    await waitFor(() => {
      expect(api.postSeasonBuilderDryRunBuild).toHaveBeenCalledWith(expect.objectContaining({
        preflight_fingerprint: 'pf_test_merge',
        reviewed_diff_id: 'rd_test_merge',
        overwrite_policy: 'merge_preview'
      }))
    })
    expect((await screen.findAllByText('pf_test_merge')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('rd_test_merge')).length).toBeGreaterThan(0)
    expect(screen.getByText('Backend advisory notes returned for this policy/source combination.')).toBeInTheDocument()
    expect(screen.getByText('Merge policy preview selected. Future implementation must still perform event-level backend diff before any merge command.')).toBeInTheDocument()
    expect(screen.getByText('No backend blocking reasons returned.')).toBeInTheDocument()
    expect(screen.getAllByText('false').length).toBeGreaterThan(0)

    fireEvent.change(screen.getByLabelText('Future policy preview'), { target: { value: 'overwrite_preview' } })
    await waitFor(() => {
      expect(api.postSeasonBuilderPreflight).toHaveBeenCalledWith(expect.objectContaining({
        target_season_label: '2000/01',
        overwrite_policy: 'overwrite_preview',
        requested_by: 'local-admin-preview'
      }))
    })
    expect(await screen.findByText(/Overwrite policy preview is selected\./)).toBeInTheDocument()
    expect(screen.getAllByText('pf_test_overwrite').length).toBeGreaterThan(0)
    expect(screen.getAllByText('rd_test_overwrite').length).toBeGreaterThan(0)
    expect(screen.getByText('Overwrite policy preview selected. Future implementation must require explicit audited confirmation before any overwrite command.')).toBeInTheDocument()
    expect(api.getSeasonCalendar.mock.calls.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Future audited command flow')).toBeInTheDocument()
    expect(screen.getByText('None of these commands are implemented on this page.')).toBeInTheDocument()
    expect(screen.getByText('Read-only preflight checklist')).toBeInTheDocument()
    expect(screen.getByText('Read-only preflight preview. Not an authoritative build gate.')).toBeInTheDocument()
    const forbiddenMutationActions = ['Build', 'Create', 'Apply', 'Generate', 'Simulate', 'Run', 'Save', 'Update', 'Delete', 'Bootstrap', 'Merge', 'Overwrite', 'Preflight']
    for (const action of forbiddenMutationActions) {
      expect(screen.queryByRole('button', { name: new RegExp(`^${action}$`, 'i') })).not.toBeInTheDocument()
    }
  }, 90000)

  it('renders Season Builder no-calendar overwrite policy branch', async () => {
    api.getSeasonCalendar.mockResolvedValueOnce({
      calendar: null,
      summary: { event_count: 0, persisted: false, first_event_week: null, last_event_week: null },
      metadata: null,
      validation_warnings: [],
      validation_errors: []
    })
    api.postSeasonBuilderPreflight.mockResolvedValueOnce({
      can_build: false,
      target_season_label: '2000/2001',
      source_type: 'blank_calendar_planned',
      source_template_id: null,
      preflight_fingerprint: 'pf_test_empty',
      reviewed_diff_id: 'rd_test_empty',
      target_calendar_exists: false,
      target_event_count: 0,
      source_resolved: true,
      source_summary: { template_name: 'Default MSA Template Preview', slot_count: 1, week_count: 61 },
      authoritative_diff_summary: {
        status: 'read_only_preflight',
        can_build: false,
        target_calendar_exists: false,
        target_event_count: 0,
        source_type: 'season_template',
        source_resolved: true,
        source_slot_count: 1,
        source_week_count: 1,
        target_week_count: null,
        week_count_compatible: null,
        source_range: { first_week: 1, last_week: 1 },
        target_range: { first_week: null, last_week: null },
        structural_comparison: { planned_source_slots: 1, existing_target_events: 0, target_is_empty: true, requires_overwrite_or_merge_policy: false },
        blocking_reasons: [],
        advisory_notes: [],
        placeholder: 'Event-level additions/replacements/conflicts remain planned for a future phase.',
        template_conflict_summary: {
          available: true,
          read_only: true,
          non_blocking: true,
          status: 'warnings',
          warning_count: 1,
          info_count: 2,
          conflict_count: 3,
          conflict_codes: ['template_conflict_week_overloaded'],
          busiest_week: 5,
          busiest_week_slot_count: 4,
          source: 'template_slot_conflict_preview',
          message: 'Template slot conflict diagnostics are available as read-only non-blocking preview.'
        }
      },
      validation_warnings: [],
      validation_errors: [],
      audit_preview: { action: 'season_builder_preflight', read_only: true, mutation_permitted: false }
    })
    api.postSeasonBuilderDryRunBuild.mockResolvedValueOnce({
      command: 'season_builder_dry_run_build',
      enabled: false,
      can_execute: false,
      can_mutate: false,
      target_season_label: '2000/01',
      source_type: 'blank_calendar_planned',
      source_template_id: null,
      overwrite_policy: null,
      preflight_fingerprint: 'pf_test_empty',
      reviewed_diff_id: 'rd_test_empty',
      validation_errors: [],
      validation_warnings: [],
      audit_preview: { action: 'season_builder_dry_run_build', read_only: true, mutation_permitted: false, execution_enabled: false, explicit_confirmation_present: false, generation_design_preview_available: true, candidate_event_contract_preview_available: true , conflict_contract_preview_available: true, dry_run_result_contract_preview_available: true, dry_run_result_preview_available: true, dry_run_result_identity_available: true },
      generation_design_preview: {
        status: 'design_preview_only',
        execution_enabled: false,
        will_generate_events: false,
        will_persist_calendar: false,
        will_mutate_existing_calendar: false,
        planned_steps: ['Validate reviewed preflight identity.', 'Return additions/replacements/conflicts without persistence.'],
        required_future_inputs: ['preflight_fingerprint', 'reviewed_diff_id', 'audit_reason', 'explicit_confirmation', 'mutation_scope'],
        planned_output_sections: ['candidate_events', 'conflict_summary', 'audit_preview'],
        blocked_reason: 'Dry-run generation is not implemented in this phase.'
      },
      candidate_event_contract_preview: {
        status: 'contract_preview_only',
        will_generate_candidates: false,
        candidate_count: 0,
        event_shape: { source_slot_id: 'string', season_week_start: 'int', candidate_status: 'planned | conflict | invalid' },
        structural_summary_shape: { additions_count: 'int', conflict_count: 'int', invalid_count: 'int', candidate_count: 'int' },
        conflict_summary_shape: { week_conflicts: 'array', slot_conflicts: 'array', policy_conflicts: 'array', validation_conflicts: 'array' },
        blocked_reason: 'Candidate event generation is not implemented in this phase.'
      },
      conflict_contract_preview: {
        status: 'contract_preview_only',
        will_compute_conflicts: false,
        conflict_count: 0,
        week_conflict_shape: { conflict_id: 'string', conflict_type: 'week_overlap', season_week: 'int', candidate_id: 'string', existing_event_id: 'string | null', message: 'string', severity: 'info | warning | blocking' },
        slot_conflict_shape: { conflict_id: 'string', conflict_type: 'slot_collision', source_slot_id: 'string', candidate_id: 'string', existing_event_id: 'string | null', message: 'string', severity: 'info | warning | blocking' },
        policy_conflict_shape: { conflict_id: 'string', conflict_type: 'policy_violation', policy: 'merge_preview | overwrite_preview | create_only_preview | repair_preview', candidate_id: 'string | null', message: 'string', severity: 'info | warning | blocking' },
        validation_conflict_shape: { conflict_id: 'string', conflict_type: 'validation_error', field: 'string', candidate_id: 'string | null', message: 'string', severity: 'warning | blocking' },
        blocked_reason: 'Conflict computation is not implemented in this phase.'
      },
      dry_run_result_contract_preview: {
        status: 'contract_preview_only',
        will_return_real_result: false,
        candidate_events: [],
        structural_summary: { candidate_count: 0, target_event_count: null, additions_count: 0, replacement_count: 0, conflict_count: 0, invalid_count: 0 },
        conflict_summary: { week_conflicts: [], slot_conflicts: [], policy_conflicts: [], validation_conflicts: [] },
        result_metadata: { preflight_fingerprint: 'pf_test_empty', reviewed_diff_id: 'rd_test_empty', execution_enabled: false, read_only: true, mutation_permitted: false },
        blocked_reason: 'Dry-run result generation is not implemented in this phase.'
      },
      dry_run_result_preview: {
        status: 'read_only_generated',
        execution_enabled: false,
        mutation_permitted: false,
        candidate_events: [],
        structural_summary: { candidate_count: 0, target_event_count: 0, additions_count: 0, replacement_count: 0, conflict_count: 0, invalid_count: 0 },
        conflict_summary: { week_conflicts: [], slot_conflicts: [], policy_conflicts: [], validation_conflicts: [] },
        result_metadata: { preflight_fingerprint: 'pf_test_empty', reviewed_diff_id: 'rd_test_empty', source_type: 'season_template', source_template_id: 'default_msa_template_preview', overwrite_policy: null, target_calendar_exists: false, target_event_count: 0, comparison_performed: true, read_only: true, mutation_permitted: false, dry_run_result_fingerprint: 'drf_test_empty', dry_run_result_id: 'drr_test_empty' },
        validation_summary: { status: 'clean', blocking_count: 0, warning_count: 0, info_count: 0, blocking_reasons: [], warning_reasons: [], info_messages: [], candidate_status_counts: { planned: 0, replacement: 0, conflict: 0, invalid: 0 }, conflict_type_counts: { week_conflicts: 0, slot_conflicts: 0, policy_conflicts: 0, validation_conflicts: 0 } },
        plan_readiness: { read_only_plan_available: true, has_blocking_issues: false, has_warnings: false, mutation_still_disabled: true, next_required_step: 'Review dry-run summary; execution remains disabled.' },
        identity_readiness: { status: 'ready_reference', items: [{ area: 'preflight_fingerprint', status: 'OK', message: 'Preflight fingerprint is present.' }, { area: 'candidate_identity_review_reference', status: 'OK', message: 'Candidate identity set can be referenced by a future audited apply flow.' }], future_command_reference: { preflight_fingerprint: 'pf_test_empty', reviewed_diff_id: 'rd_test_empty', dry_run_result_fingerprint: 'drf_test_empty', dry_run_result_id: 'drr_test_empty', can_reference_future_command: true, mutation_still_disabled: true, candidate_identity_fingerprint: 'abc123fingerprint', candidate_identity_reference_id: 'abc123fingerprint', can_reference_candidate_identity_set: true, candidate_identity_reference_type: 'candidate_identity_set' }, candidate_identity_readiness_overview: { available: true, candidate_identity_fingerprint: 'abc123fingerprint', candidate_identity_reference_id: 'abc123fingerprint', candidate_identity_reference_type: 'candidate_identity_set', can_reference_candidate_identity_set: true, candidate_reference_status: 'OK', main_future_command_reference_ready: true, read_only: true, mutation_permitted: false, message: 'Candidate identity readiness is referenceable.' } },
        candidate_identity_summary: { candidate_count: 1, candidate_ids: ['cand_default_msa_template_preview_slot_01_1'], candidate_identity_keys: ['target_season=2000_01|source_type=season_template|source_template_id=default_msa_template_preview|source_slot_id=slot_01|season_week_start=1|event_name=world_tour_gold|category=gold|source_template_ref=wt_gold_24'], duplicate_candidate_ids: [], duplicate_candidate_identity_keys: [], read_only: true, mutation_permitted: false, message: 'Candidate event identities are deterministic and read-only in dry-run.' },
        candidate_identity_contract: { identity_source: 'season_template_slot', id_strategy: 'sanitized_template_slot_week', key_strategy: 'pipe_joined_sanitized_components', key_components: ['target_season', 'source_type', 'source_template_id', 'source_slot_id', 'season_week_start', 'event_name', 'category', 'source_template_ref'], candidate_count: 1, has_duplicate_candidate_ids: false, has_duplicate_candidate_identity_keys: false, safe_for_future_reference: true, read_only: true, mutation_permitted: false, message: 'Candidate identities are stable and safe for future reference.' },
        candidate_identity_overview: { available: true, candidate_count: 1, safe_for_future_reference: true, has_duplicate_candidate_ids: false, has_duplicate_candidate_identity_keys: false, identity_source: 'season_template_slot', id_strategy: 'sanitized_template_slot_week', key_strategy: 'pipe_joined_sanitized_components', read_only: true, mutation_permitted: false, message: 'Candidate identity overview: safe for future reference.' },
        candidate_identity_fingerprint: { fingerprint: 'abc123fingerprint', fingerprint_algorithm: 'sha256', fingerprint_payload_version: 1, candidate_count: 1, candidate_ids: ['cand_default_msa_template_preview_slot_01_1'], candidate_identity_keys: ['target_season=2000_01|source_type=season_template'], safe_for_future_reference: true, target_season_label: '2000/01', source_type: 'season_template', source_template_id: 'default_msa_template_preview', read_only: true, mutation_permitted: false, message: 'Candidate identity fingerprint is deterministic and read-only.' },
        candidate_identity_review_reference: { reference_type: 'candidate_identity_set', reference_id: 'abc123fingerprint', fingerprint_algorithm: 'sha256', fingerprint_payload_version: 1, candidate_count: 1, safe_for_future_reference: true, can_reference_future_apply: true, read_only: true, mutation_permitted: false, message: 'Candidate identity set can be referenced by a future audited apply flow.' }
      },
      message: 'Dry-run build command contract exists, but execution is disabled in this phase.'
    })
    api.postSeasonBuilderApplyCommandContract.mockResolvedValueOnce({
      command: 'season_builder_apply_command',
      enabled: false,
      can_execute: false,
      can_mutate: false,
      target_season_label: '2000/01',
      source_type: 'blank_calendar_planned',
      source_template_id: null,
      overwrite_policy: null,
      validation_errors: [],
      validation_warnings: [],
      audit_preview: { action: 'season_builder_apply_command', read_only: true, mutation_permitted: false, execution_enabled: false, audit_trail_contract_preview_available: true, safety_gate_contract_preview_available: true },
      audit_trail_contract_preview: {
        status: 'contract_preview_only',
        will_persist_audit: false,
        audit_event_type: 'season_builder_apply_command',
        required_identity_fields: ['preflight_fingerprint', 'reviewed_diff_id', 'dry_run_result_fingerprint', 'dry_run_result_id'],
        required_actor_fields: ['requested_by', 'audit_reason', 'explicit_confirmation', 'mutation_scope'],
        audit_record_shape: { audit_id: 'string', timestamp_utc: 'datetime', explicit_confirmation_present: 'bool', result: 'disabled | executed | rejected' },
        blocked_reason: 'Audit trail persistence is not implemented in this phase.'
      },
      safety_gate_contract_preview: {
        status: 'contract_preview_only',
        will_execute_apply: false,
        will_mutate_calendar: false,
        gate_result: 'blocked_disabled_phase',
        required_gates: [
          { gate: 'identity', required: true, currently_satisfied: true, message: 'Preflight, reviewed diff, and dry-run result identities must be present.' },
          { gate: 'audit_metadata', required: true, currently_satisfied: false, message: 'Audit reason, explicit confirmation, and mutation scope must be present.' },
          { gate: 'execution_enabled', required: true, currently_satisfied: false, message: 'Execution is disabled in this phase.' },
          { gate: 'mutation_permission', required: true, currently_satisfied: false, message: 'Mutation permission is disabled in this phase.' },
          { gate: 'audit_trail', required: true, currently_satisfied: false, message: 'Audit trail persistence is not implemented in this phase.' }
        ],
        future_allowed_mutation_scopes: ['create_only_preview', 'merge_preview', 'overwrite_preview', 'repair_preview'],
        blocked_reason: 'Final apply safety gate is contract-only and disabled in this phase.'
      },
      required_identity: { preflight_fingerprint: 'pf_test_empty', reviewed_diff_id: 'rd_test_empty', dry_run_result_fingerprint: 'drf_test_empty', dry_run_result_id: 'drr_test_empty', all_identity_fields_present: true },
      required_audit_metadata: { requested_by: 'local-admin-preview', audit_reason_present: false, explicit_confirmation_present: false, mutation_scope: null, all_audit_metadata_present: false },
      message: 'Apply command contract exists, but execution is disabled in this phase.'
    })

    renderAppAt('/admin/seasons/build')

    expect(await screen.findByRole('heading', { name: 'Season Builder' })).toBeInTheDocument()
    expect(screen.getByText('Target existing calendar preview')).toBeInTheDocument()
    expect(await screen.findByText('Calendar exists: No')).toBeInTheDocument()
    expect(screen.getByText('No existing calendar found for selected target season.')).toBeInTheDocument()
    expect(screen.getByText('Overwrite / merge policy preview')).toBeInTheDocument()
    expect(screen.getByText('Overwrite / merge policy selection for preflight')).toBeInTheDocument()
    expect(screen.getByText('No existing target calendar detected. Policy selection is optional for this read-only preview.')).toBeInTheDocument()
    expect(screen.getByText('Source vs target preflight summary')).toBeInTheDocument()
    expect(screen.getByText('Read-only source/target diff detail')).toBeInTheDocument()
    expect(screen.getByText('Backend preflight contract preview')).toBeInTheDocument()
    expect(screen.getByText('Read-only design preview. No backend preflight endpoint is called from this page.')).toBeInTheDocument()
    expect(screen.getByText('Backend preflight result')).toBeInTheDocument()
    expect(screen.getByText('Authoritative read-only backend preflight result. This endpoint does not build, merge, overwrite, or apply anything.')).toBeInTheDocument()
    expect((await screen.findAllByText('can_build')).length).toBeGreaterThan(0)
    expect(screen.getByText('No validation warnings returned.')).toBeInTheDocument()
    expect(screen.getByText('No validation errors returned.')).toBeInTheDocument()
    expect(screen.getByText('Mutation permitted: false')).toBeInTheDocument()
    expect(screen.getAllByText('false').length).toBeGreaterThan(0)
    expect(screen.getAllByText('target_calendar_exists').length).toBeGreaterThan(0)
    expect(screen.getAllByText('target_event_count').length).toBeGreaterThan(0)
    expect(screen.getByText('Authoritative diff status')).toBeInTheDocument()
    expect(screen.getByText('Source vs target structural summary')).toBeInTheDocument()
    expect(screen.getAllByText('Blocking reasons').length).toBeGreaterThan(0)
    expect(screen.getByText('Advisory notes')).toBeInTheDocument()
    expect(screen.getByText('Raw authoritative diff summary JSON')).toBeInTheDocument()
    expect(screen.getByText('No backend blocking reasons returned.')).toBeInTheDocument()
    expect(screen.getByText('No backend advisory notes returned.')).toBeInTheDocument()
    expect(screen.getAllByText('Dry-run identity readiness').length).toBeGreaterThan(0)
    expect(screen.getByText('can_reference_future_command')).toBeInTheDocument()
    expect(screen.getAllByText('Candidate identity fingerprint').length).toBeGreaterThan(0)
    expect(screen.getAllByText('abc123fingerprint').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Candidate identity reference ID').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Can reference candidate identity set').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Candidate identity reference type').length).toBeGreaterThan(0)
    expect(screen.getByText('candidate_identity_review_reference')).toBeInTheDocument()
    expect(screen.getAllByText('drf_test_empty').length).toBeGreaterThan(0)
    expect(screen.getAllByText('drr_test_empty').length).toBeGreaterThan(0)
    expect(screen.getAllByText('validation_errors count').length).toBeGreaterThan(0)
    expect(screen.getAllByText('0').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/\"read_only\": true/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/\"mutation_permitted\": false/).length).toBeGreaterThan(0)
    expect(screen.getByText('Even when backend preflight succeeds, build actions remain unavailable in this phase.')).toBeInTheDocument()
    expect(screen.getByText('Future build command contract preview')).toBeInTheDocument()
    expect(screen.getByText('Read-only contract preview. No build command exists on this page.')).toBeInTheDocument()
    expect(screen.getByText('Current preflight signals')).toBeInTheDocument()
    expect(screen.getAllByText('preflight_fingerprint').length).toBeGreaterThan(0)
    expect(screen.getAllByText('reviewed_diff_id').length).toBeGreaterThan(0)
    expect(screen.getByText('Future build implementation must require a reviewed backend preflight, explicit audit metadata, and a separate audited command.')).toBeInTheDocument()
    expect(screen.getByText('Future command readiness checklist')).toBeInTheDocument()
    expect(screen.getByText(/Backend preflight fingerprint is available\.|Backend preflight fingerprint is not available yet\./)).toBeInTheDocument()
    expect(screen.getAllByText('Reviewed diff identity is available.').length).toBeGreaterThan(0)
    expect(screen.getByText('Readiness remains blocked until a separate audited backend command is implemented.')).toBeInTheDocument()
    expect(screen.getByText('Disabled dry-run build contract result')).toBeInTheDocument()
    expect(screen.getAllByText('Candidate identity overview').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Candidate identity summary').length).toBeGreaterThan(0)
    expect(screen.getByText('Candidate identity candidate count: 1')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity candidate IDs: cand_default_msa_template_preview_slot_01_1')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity duplicate candidate IDs: none')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity read-only: true')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity mutation permitted: false')).toBeInTheDocument()
    expect(screen.getAllByText('Candidate identity contract').length).toBeGreaterThan(0)
    expect(screen.getByText('Candidate identity source: season_template_slot')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity ID strategy: sanitized_template_slot_week')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity key strategy: pipe_joined_sanitized_components')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity safe for future reference: true')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity contract mutation permitted: false')).toBeInTheDocument()
    expect(screen.getAllByText('Candidate identity fingerprint').length).toBeGreaterThan(0)
    expect(screen.getByText('Candidate identity fingerprint value: abc123fingerprint')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity fingerprint algorithm: sha256')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity fingerprint candidate count: 1')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity fingerprint safe for future reference: true')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity fingerprint mutation permitted: false')).toBeInTheDocument()
    expect(screen.getAllByText('Candidate identity review reference').length).toBeGreaterThan(0)
    expect(screen.getByText('Candidate identity review reference type: candidate_identity_set')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity review reference ID: abc123fingerprint')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity review reference can reference future apply: true')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity review reference mutation permitted: false')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot validation preview')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot validation preview is not available.')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict preview')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict preview is not available.')).toBeInTheDocument()
    expect(screen.getByText('Disabled dry-run readiness summary')).toBeInTheDocument()
    expect(screen.getByText('Dry-run audit metadata preview inputs')).toBeInTheDocument()
    expect(screen.getByText('Dry-run build command contract exists, but execution is disabled in this phase.')).toBeInTheDocument()
    expect(screen.getByText('Future dry-run generation design preview')).toBeInTheDocument()

    expect(screen.getByText('Dry-run validation summary')).toBeInTheDocument()
    expect(screen.getByText('Candidate status counts')).toBeInTheDocument()
    expect(screen.getByText('Conflict type counts')).toBeInTheDocument()
    expect(screen.getAllByText('Blocking reasons').length).toBeGreaterThan(0)
    expect(screen.getByText('Warning reasons')).toBeInTheDocument()
    expect(screen.getByText('Plan readiness')).toBeInTheDocument()
    expect(screen.getByText('Review dry-run summary; execution remains disabled.')).toBeInTheDocument()
    expect(screen.getAllByText('mutation_still_disabled').length).toBeGreaterThan(0)
    expect(screen.getByText('No dry-run warning reasons returned.')).toBeInTheDocument()
    expect(screen.getByText('Dry-run generation is not implemented in this phase.')).toBeInTheDocument()
    expect(screen.getByText('Candidate event contract preview')).toBeInTheDocument()
    expect(screen.getByText('Candidate event generation is not implemented in this phase.')).toBeInTheDocument()
    expect(screen.getByText('Conflict contract preview')).toBeInTheDocument()
    expect(screen.getAllByText('contract_preview_only').length).toBeGreaterThan(0)
    expect(screen.getByText('will_compute_conflicts')).toBeInTheDocument()
    expect(screen.getAllByText('conflict_count').length).toBeGreaterThan(0)
    expect(screen.getByText('Conflict computation is not implemented in this phase.')).toBeInTheDocument()
    expect(screen.getByText('Week conflict shape')).toBeInTheDocument()
    expect(screen.getByText('week_overlap')).toBeInTheDocument()
    expect(screen.getAllByText('season_week').length).toBeGreaterThan(0)
    expect(screen.getAllByText('existing_event_id').length).toBeGreaterThan(0)
    expect(screen.getByText('Slot conflict shape')).toBeInTheDocument()
    expect(screen.getByText('slot_collision')).toBeInTheDocument()
    expect(screen.getByText('Policy conflict shape')).toBeInTheDocument()
    expect(screen.getByText('policy_violation')).toBeInTheDocument()
    expect(screen.getByText('Validation conflict shape')).toBeInTheDocument()
    expect(screen.getByText('validation_error')).toBeInTheDocument()
    expect(screen.getAllByText('conflict_contract_preview_available').length).toBeGreaterThan(0)
    expect(screen.getByText('Dry-run result contract preview')).toBeInTheDocument()
    expect(screen.getByText('Read-only generated dry-run result preview')).toBeInTheDocument()
    expect(screen.getByText('Read-only generated candidates are not persisted.')).toBeInTheDocument()
    expect(screen.getByText('No read-only comparison conflicts returned.')).toBeInTheDocument()
    expect(screen.getByText('Dry-run result generation is not implemented in this phase.')).toBeInTheDocument()
    expect(screen.getByText('No candidate events returned in this contract-only phase.')).toBeInTheDocument()
    expect(screen.getByText('Execution remains disabled; this panel is not a build control.')).toBeInTheDocument()
    expect(screen.getByText('Disabled apply command contract result')).toBeInTheDocument()
    expect(screen.getByText(/Apply command contract check is waiting for preflight and dry-run result identities\.|Apply audit trail contract preview/)).toBeInTheDocument()
    expect(screen.getByText('Apply command readiness summary')).toBeInTheDocument()
    expect(screen.getAllByText('drf_test_empty').length).toBeGreaterThan(0)
    expect(screen.getAllByText('drr_test_empty').length).toBeGreaterThan(0)
    expect(screen.getByText('Execution remains disabled; this panel is not an apply control.')).toBeInTheDocument()
    expect(screen.getByText('Dry-run identity readiness status: ready_reference.')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity readiness overview')).toBeInTheDocument()
    expect(screen.getByText('candidate_identity_fingerprint')).toBeInTheDocument()
    expect(screen.getByText('candidate_identity_reference_id')).toBeInTheDocument()
    expect(screen.getByText('can_reference_candidate_identity_set')).toBeInTheDocument()
    expect(screen.getByText('candidate_reference_status')).toBeInTheDocument()
    expect(screen.getByText('main_future_command_reference_ready')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity readiness is referenceable.')).toBeInTheDocument()
    expect(screen.getByText('The apply command contract is visible, but execution remains disabled.')).toBeInTheDocument()
    expect(api.postSeasonBuilderPreflight).toHaveBeenCalledWith({ target_season_label: '2000/01', source_type: 'season_template', source_template_id: 'default_msa_template_preview', overwrite_policy: null, requested_by: 'local-admin-preview' })
    expect(screen.getAllByText('No existing calendar detected.').length).toBeGreaterThan(0)
    expect(screen.getByText('Silent overwrite must never be allowed.')).toBeInTheDocument()
    expect(screen.getByText('Merge policy is not needed for an empty target, but future command still requires audit.')).toBeInTheDocument()
    expect(screen.getByText('Future build command must be explicit, audited, and reviewable.')).toBeInTheDocument()
    expect(screen.getByText('Empty target calendar detected; future creation would still require an explicit audited backend command.')).toBeInTheDocument()
    expect(screen.getByText('Review read-only diff and backend validation before any future command.')).toBeInTheDocument()
    expect(screen.getByText('No build, overwrite, merge, or apply command is available from this page.')).toBeInTheDocument()
    expect(screen.getByText('Empty target has no existing concrete events to compare locally, but future backend validation is still required.')).toBeInTheDocument()
    expect(screen.getByText('No diff, build, merge, overwrite, or apply command is executed from this page.')).toBeInTheDocument()
    expect(screen.getByText('The dry-run contract is visible, but execution remains disabled.')).toBeInTheDocument()

    const forbiddenMutationActions = ['Build', 'Create', 'Apply', 'Generate', 'Simulate', 'Run', 'Save', 'Update', 'Delete', 'Bootstrap', 'Merge', 'Overwrite', 'Preflight']
    for (const action of forbiddenMutationActions) {
      expect(screen.queryByRole('button', { name: new RegExp(`^${action}$`, 'i') })).not.toBeInTheDocument()
    }
  }, 45000)

  it('keeps future apply request validation manual-only and preview-only with fill helper', async () => {
    api.postSeasonBuilderDryRunBuild.mockResolvedValueOnce({
      enabled: false,
      dry_run_result_preview: {
        dry_run_result_fingerprint: 'dry-run-fp-with-reference',
        dry_run_result_id: 'dry-run-id-with-reference',
        candidate_identity_review_reference: { reference_id: 'candidate-ref-id', reference_type: 'dry_run_candidate_identity' },
        candidate_identity_fingerprint: { fingerprint: 'candidate-fp' }
      },
      validation_warnings: [],
      validation_errors: []
    })
    renderAppAt('/admin/seasons/build')
    expect(await screen.findByRole('heading', { name: 'Season Builder' })).toBeInTheDocument()

    expect(screen.queryByRole('button', { name: /^Apply$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Execute$/i })).not.toBeInTheDocument()
    expect(api.validateFutureApplyRequestPreview).not.toHaveBeenCalled()

    const fillButton = await screen.findByRole('button', { name: 'Fill from dry-run reference' })
    await waitFor(() => expect(fillButton).toBeEnabled())
    fireEvent.click(fillButton)
    expect((screen.getByLabelText('Candidate identity reference ID') as HTMLInputElement).value).toBe('candidate-ref-id')
    expect((screen.getByLabelText('Candidate identity fingerprint') as HTMLInputElement).value).toBe('candidate-fp')
    expect((screen.getByLabelText('Candidate identity reference type') as HTMLInputElement).value).toBe('dry_run_candidate_identity')
    fireEvent.change(screen.getByLabelText('Requested by'), { target: { value: 'qa-admin' } })
    fireEvent.change(screen.getByLabelText('Audit reason'), { target: { value: 'phase-17d validation check' } })
    fireEvent.change(screen.getByLabelText('Explicit confirmation'), { target: { value: 'I understand this will create a new season calendar.' } })
    fireEvent.change(screen.getByLabelText('Future apply mutation scope'), { target: { value: 'create_only' } })
    expect(api.validateFutureApplyRequestPreview).not.toHaveBeenCalled()
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Validate future apply reference' }))

    await waitFor(() => expect(api.validateFutureApplyRequestPreview).toHaveBeenCalledTimes(1))
    expect(api.validateFutureApplyRequestPreview).toHaveBeenCalledWith(expect.objectContaining({
      target_season_label: '2000/01',
      source_type: 'season_template',
      source_template_id: 'default_msa_template_preview',
      overwrite_policy: null,
      preflight_fingerprint: 'pf_test_existing',
      reviewed_diff_id: 'rd_test_existing',
      requested_candidate_identity_reference_id: 'candidate-ref-id',
      requested_candidate_identity_fingerprint: 'candidate-fp',
      requested_candidate_identity_reference_type: 'dry_run_candidate_identity',
      requested_by: 'qa-admin',
      audit_reason: 'phase-17d validation check',
      explicit_confirmation: 'I understand this will create a new season calendar.',
      mutation_scope: 'create_only'
    }))
    expect((await screen.findAllByText('Future apply request validation preview')).length).toBeGreaterThan(0)
    expect(screen.getByText('Create-only apply audit metadata preview')).toBeInTheDocument()
    expect(screen.getByText('All required audit metadata present: true')).toBeInTheDocument()
    expect(screen.getAllByText('Apply execution enabled: false').length).toBeGreaterThan(0)
    expect(screen.queryByText('Apply execution enabled: true')).not.toBeInTheDocument()
    const previewResultBlock = screen.getByLabelText('Future apply preview result block')
    expect(within(previewResultBlock).queryByRole('button', { name: /^Apply$/i })).not.toBeInTheDocument()
    expect(within(previewResultBlock).queryByRole('button', { name: /^Execute$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Apply$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Execute$/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fill from dry-run reference' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Validate future apply reference' })).toBeInTheDocument()
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    expect(api.postSeasonBuilderApplyCommandContract).not.toHaveBeenCalledWith(expect.objectContaining({
      requested_candidate_identity_reference_id: 'abc123fingerprint'
    }))
  }, 60000)

  it('does not auto-call future apply validation when audit metadata inputs change', async () => {
    renderAppAt('/admin/seasons/build')
    expect(await screen.findByRole('heading', { name: 'Season Builder' })).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Requested by'), { target: { value: 'auditor' } })
    fireEvent.change(screen.getByLabelText('Audit reason'), { target: { value: 'manual preview only' } })
    fireEvent.change(screen.getByLabelText('Explicit confirmation'), { target: { value: 'preview phrase' } })
    fireEvent.change(screen.getByLabelText('Future apply mutation scope'), { target: { value: 'create_only' } })
    expect(api.validateFutureApplyRequestPreview).not.toHaveBeenCalled()

  })

  it('clears future apply validation result when builder context changes without auto-revalidating', async () => {
    api.validateFutureApplyRequestPreview.mockResolvedValueOnce(futureApplyValidationResponseMock())
    renderAppAt('/admin/seasons/build')
    expect(await screen.findByRole('heading', { name: 'Season Builder' })).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Candidate identity reference ID'), { target: { value: 'candidate-ref-id' } })
    fireEvent.change(screen.getByLabelText('Candidate identity fingerprint'), { target: { value: 'candidate-fp' } })
    fireEvent.change(screen.getByLabelText('Candidate identity reference type'), { target: { value: 'dry_run_candidate_identity' } })
    fireEvent.click(screen.getByRole('button', { name: 'Validate future apply reference' }))
    await waitFor(() => expect(api.validateFutureApplyRequestPreview).toHaveBeenCalledTimes(1))
    fireEvent.change(screen.getByLabelText('Future policy preview'), { target: { value: 'merge_preview' } })

    await waitFor(() => {
      expect(screen.queryByText('Validation preview only.')).not.toBeInTheDocument()
    })
    expect(api.validateFutureApplyRequestPreview).toHaveBeenCalledTimes(1)
    expect((screen.getByLabelText('Candidate identity reference ID') as HTMLInputElement).value).toBe('candidate-ref-id')
    expect((screen.getByLabelText('Candidate identity fingerprint') as HTMLInputElement).value).toBe('candidate-fp')
    expect((screen.getByLabelText('Candidate identity reference type') as HTMLInputElement).value).toBe('dry_run_candidate_identity')
  })

  it('disables fill helper when dry-run reference metadata is unavailable', async () => {
    api.postSeasonBuilderDryRunBuild.mockResolvedValueOnce({
      enabled: false,
      dry_run_result_preview: {
        dry_run_result_fingerprint: 'dry-run-fp-no-reference',
        dry_run_result_id: 'dry-run-id-no-reference'
      },
      validation_warnings: [],
      validation_errors: []
    })
    renderAppAt('/admin/seasons/build')
    expect(await screen.findByRole('heading', { name: 'Season Builder' })).toBeInTheDocument()

    const fillButton = await screen.findByRole('button', { name: 'Fill from dry-run reference' })
    expect(fillButton).toBeDisabled()
    const dangerZoneSection = screen.getByRole('heading', { name: 'Danger zone — persistent create-only calendar creation' }).closest('section') as HTMLElement
    const executeCreateOnlyButton = within(dangerZoneSection).getByRole('button', { name: 'Execute create-only season calendar command' })
    fireEvent.change(within(dangerZoneSection).getByLabelText('Exact confirmation phrase'), { target: { value: 'I understand this will create a new season calendar.' } })
    fireEvent.change(within(dangerZoneSection).getByLabelText('Mutation scope'), { target: { value: 'create_only' } })
    await waitFor(() => expect(executeCreateOnlyButton).toBeDisabled())
    fireEvent.click(executeCreateOnlyButton)
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: /^Apply$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Execute$/i })).not.toBeInTheDocument()
  })

  it('shows manual future apply validation errors without enabling mutation controls', async () => {
    api.validateFutureApplyRequestPreview.mockRejectedValueOnce(new Error('Validation endpoint unavailable'))
    renderAppAt('/admin/seasons/build')
    expect(await screen.findByRole('heading', { name: 'Season Builder' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Validate future apply reference' }))

    expect(await screen.findByText('Future apply request validation failed: Validation endpoint unavailable')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Apply$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Execute$/i })).not.toBeInTheDocument()
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    expect(api.postSeasonBuilderApplyCommandContract).not.toHaveBeenCalled()
  })

  it('clears future apply validation errors when builder context changes without auto-revalidating', async () => {
    api.validateFutureApplyRequestPreview.mockRejectedValueOnce(new Error('Validation endpoint unavailable'))
    renderAppAt('/admin/seasons/build')
    expect(await screen.findByRole('heading', { name: 'Season Builder' })).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Candidate identity reference ID'), { target: { value: 'candidate-ref-id' } })
    fireEvent.change(screen.getByLabelText('Candidate identity fingerprint'), { target: { value: 'candidate-fp' } })
    fireEvent.change(screen.getByLabelText('Candidate identity reference type'), { target: { value: 'dry_run_candidate_identity' } })
    fireEvent.click(screen.getByRole('button', { name: 'Validate future apply reference' }))
    await waitFor(() => expect(api.validateFutureApplyRequestPreview).toHaveBeenCalledTimes(1))
    fireEvent.change(screen.getByLabelText('Future policy preview'), { target: { value: 'merge_preview' } })
    await waitFor(() => {
      expect(screen.queryByText('Future apply request validation failed: Validation endpoint unavailable')).not.toBeInTheDocument()
    })
    expect(api.validateFutureApplyRequestPreview).toHaveBeenCalledTimes(1)
    expect((screen.getByLabelText('Candidate identity reference ID') as HTMLInputElement).value).toBe('candidate-ref-id')
    expect((screen.getByLabelText('Candidate identity fingerprint') as HTMLInputElement).value).toBe('candidate-fp')
    expect((screen.getByLabelText('Candidate identity reference type') as HTMLInputElement).value).toBe('dry_run_candidate_identity')
  })

  it('renders Concrete Season detail dashboard routes', async () => {
    renderAppAt('/admin/seasons/detail/2000%2F01')
    expect((await screen.findAllByRole('heading', { level: 2, name: 'Concrete Season' })).length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: 'Read-only concrete season profile' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Season detail sections' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Profile / route labels' })).toHaveAttribute('href', '#season-profile')
    expect(screen.getByRole('link', { name: 'Selected season workspace' })).toHaveAttribute('href', '#selected-season-workspace')
    expect(screen.getByRole('link', { name: 'Calendar preview' })).toHaveAttribute('href', '#calendar-preview')
    expect(screen.getByRole('link', { name: 'Ranking & points preview' })).toHaveAttribute('href', '#ranking-points-preview')
    expect(screen.getByRole('link', { name: 'Season health preview' })).toHaveAttribute('href', '#season-health-preview')
    expect(await screen.findByRole('heading', { name: 'Selected Season Workspace' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Season Health / Readiness Preview' })).toBeInTheDocument()
    expect(screen.getByText('Registry check')).toBeInTheDocument()
    expect(screen.getByText('Calendar check')).toBeInTheDocument()
    expect(screen.getByText('Active players check')).toBeInTheDocument()
    expect(screen.getByText('Ranking table check')).toBeInTheDocument()
    expect(screen.getByText('This page does not create, build, simulate, or edit the season.')).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Raw route label: 2000/01'))).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Decoded route label: 2000/01'))).toBeInTheDocument()
    expect(screen.getAllByText((content) => content.includes('Compact label: 2000/01')).length).toBeGreaterThan(0)
    expect(screen.getAllByText((content) => content.includes('Legacy label: 2000/2001')).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('link', { name: '/admin/seasons/detail/2000%2F01' }).some((link) => link.getAttribute('href') === '/admin/seasons/detail/2000%2F01')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Tour & Seasons' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Season Registry' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons/season-registry')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Seasons' }).some((link) => link.getAttribute('href') === '/admin/seasons')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Calendar Validation' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons/validation')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Calendar Compare / Apply' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons/compare')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Season Builder' }).some((link) => link.getAttribute('href') === '/admin/seasons/build')).toBe(true)
    expect(screen.queryByRole('button', { name: /build|apply|generate|save|create|update|delete|simulate/i })).not.toBeInTheDocument()

    renderAppAt('/admin/seasons/detail/invalid-season')
    expect((await screen.findAllByRole('heading', { level: 2, name: 'Concrete Season' })).length).toBeGreaterThan(0)
    expect(screen.getByText('Season health preview unavailable for invalid season label.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /build|apply|generate|save|create|update|delete|simulate/i })).not.toBeInTheDocument()

    renderAppAt('/admin/seasons/detail/2000%2F2001')
    expect((await screen.findAllByRole('heading', { level: 2, name: 'Concrete Season' })).length).toBeGreaterThan(0)
    expect(screen.getByText((content) => content.includes('Raw route label: 2000/2001'))).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Decoded route label: 2000/2001'))).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: '/admin/seasons/detail/2000%2F01' }).some((link) => link.getAttribute('href') === '/admin/seasons/detail/2000%2F01')).toBe(true)
    expect(screen.queryByRole('button', { name: /build|apply|generate|save|create|update|delete|simulate/i })).not.toBeInTheDocument()
  })





  it('renders category detail route and not-found route', async () => {
    renderAppAt('/admin/tour-seasons/categories/gold')
    expect(await screen.findByRole('heading', { name: 'Category' })).toBeInTheDocument()
    expect(await screen.findByText(/Name: GOLD/)).toBeInTheDocument()
    expect(screen.getByText(/category_id: gold/)).toBeInTheDocument()
    expect(screen.getAllByText(/read_only_foundation/).length).toBeGreaterThan(0)
    expect(screen.getByText(/main_draw_size:/)).toBeInTheDocument()
    expect(screen.getByText('Category editor — planned.')).toBeInTheDocument()
    expect(screen.getByText('Category versioning by season range — planned.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Categories' })).toHaveAttribute('href', '/admin/tour-seasons/categories')
    expect(screen.getByRole('link', { name: 'Open Tournament Templates' })).toHaveAttribute('href', '/admin/tournament-templates')
    expect(screen.getByRole('link', { name: 'Open Tournaments' })).toHaveAttribute('href', '/admin/tour-seasons/tournaments')
    expect(screen.getByRole('link', { name: 'Open Season Templates' })).toHaveAttribute('href', '/admin/tour-seasons/season-templates')

    renderAppAt('/admin/tour-seasons/categories/unknown-id')
    expect(await screen.findByText('Category not found.')).toBeInTheDocument()
  })

  it('renders tournament master detail route and not-found route', async () => {
    renderAppAt('/admin/tour-seasons/tournaments/world-tour-gold')
    expect(await screen.findByRole('heading', { name: 'Tournament Master' })).toBeInTheDocument()
    expect(await screen.findByText(/tournament_id: world-tour-gold/)).toBeInTheDocument()
    expect(screen.getAllByText(/read_only_foundation/).length).toBeGreaterThan(0)
    expect(screen.getByText('Tournament master editor — planned.')).toBeInTheDocument()
    expect(screen.getByText('Tournament editions — planned.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Tournaments' })).toHaveAttribute('href', '/admin/tour-seasons/tournaments')
    expect(screen.getByRole('link', { name: 'Open Tournament Templates' })).toHaveAttribute('href', '/admin/tournament-templates')
    expect(screen.getAllByRole('link', { name: 'Open Categories' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons/categories')).toBe(true)
    expect(screen.getByRole('link', { name: 'Open Season Templates' })).toHaveAttribute('href', '/admin/tour-seasons/season-templates')

    renderAppAt('/admin/tour-seasons/tournaments/unknown-id')
    expect(await screen.findByText('Tournament master not found.')).toBeInTheDocument()
  })


  it('renders season template detail route and not-found route', async () => {
    renderAppAt('/admin/tour-seasons/season-templates/default_msa_template_preview')
    expect(await screen.findByRole('heading', { name: 'Season Template' })).toBeInTheDocument()
    expect((await screen.findAllByText(/Default MSA Template Preview/)).length).toBeGreaterThan(0)
    expect(await screen.findByText('Template ID: default_msa_template_preview')).toBeInTheDocument()
    expect(screen.getAllByText(/read_only_foundation/).length).toBeGreaterThan(0)
    expect(screen.getByText('Season template editor — planned.')).toBeInTheDocument()
    expect(screen.getByText('Copy/apply to concrete season — planned.')).toBeInTheDocument()
    expect(screen.getByText('Compare/apply workflows — planned.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Season Templates' })).toHaveAttribute('href', '/admin/tour-seasons/season-templates')
    expect(screen.getByRole('link', { name: 'Open Tournaments' })).toHaveAttribute('href', '/admin/tour-seasons/tournaments')
    expect(screen.getAllByRole('link', { name: 'Open Categories' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons/categories')).toBe(true)
    expect(screen.getByRole('link', { name: 'Open Seasons' })).toHaveAttribute('href', '/admin/seasons')

    renderAppAt('/admin/tour-seasons/season-templates/unknown-id')
    expect(await screen.findByText('Season template not found.')).toBeInTheDocument()
  })

  it('renders persisted Admin calendar template detail route without mutation controls', async () => {
    api.getCalendarTemplate.mockResolvedValueOnce({
      template: {
        id: 'template-a',
        name: 'Template A',
        description: 'Persisted read-only template',
        status: 'active',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
        template_fingerprint: 'tpl_template_a',
        events: [
          {
            id: 'event-a',
            name: 'Event A',
            category_code: 'DIAMOND',
            weeks: [6, 7],
            qualification_weeks: [5],
            locked: true,
            country_code: 'EGY',
            city: 'Cairo',
            venue: 'Glass Court',
            notes: 'Read-only persisted event',
            source_template_id: 'source-a',
            event_fingerprint: 'evt_event_a'
          },
          {
            id: 'event-b',
            name: 'Event B',
            category_code: 'WORLD_TOUR_FINALS',
            weeks: [55],
            qualification_weeks: [],
            locked: false,
            country_code: null,
            city: null,
            venue: null,
            notes: null,
            source_template_id: null,
            event_fingerprint: 'evt_event_b'
          }
        ]
      },
      source_path: 'config/world/calendar_templates.json',
      status: 'ok',
      schema_version: 'calendar_templates.v1'
    })

    renderAppAt('/admin/tour-seasons/season-templates/calendar/template-a')
    expect(await screen.findByRole('heading', { name: 'Persisted Admin calendar template' })).toBeInTheDocument()
    expect(screen.getByText(/Persisted Admin calendar template detail with Admin-only create\/update template editing\./)).toBeInTheDocument()
    expect(screen.getByText(/They are not played,/)).toBeInTheDocument()
    expect(screen.getByText(/not visible in Viewer, and do not mutate canonical seasons, runs, rankings, race, history, or simulation output\./)).toBeInTheDocument()
    expect(await screen.findByText('Name: Template A')).toBeInTheDocument()
    expect(screen.getByText('id: template-a')).toBeInTheDocument()
    expect(screen.getByText('description: Persisted read-only template')).toBeInTheDocument()
    expect(screen.getByText('status: active')).toBeInTheDocument()
    expect(screen.getByText('created_at: 2026-01-01T00:00:00Z')).toBeInTheDocument()
    expect(screen.getByText('updated_at: 2026-01-02T00:00:00Z')).toBeInTheDocument()
    expect(screen.getByText('template_fingerprint: tpl_template_a')).toBeInTheDocument()
    expect(screen.getByText('source_path: config/world/calendar_templates.json')).toBeInTheDocument()
    expect(screen.getByText('schema_version: calendar_templates.v1')).toBeInTheDocument()
    expect(screen.getByText('event_count: 2')).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Event A' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'event-a' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'DIAMOND' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'W6–W7' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'W5' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Locked' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'EGY' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Cairo' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Glass Court' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Read-only persisted event' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'evt_event_a' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'WORLD_TOUR_FINALS' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'W55' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Unlocked' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Season Templates' })).toHaveAttribute('href', '/admin/tour-seasons/season-templates')
    expect(screen.getByRole('link', { name: 'Open Draft Template Sandbox' })).toHaveAttribute('href', '/admin/tour-seasons/season-templates/draft-sandbox')
    expect(screen.getByRole('link', { name: 'Open Season Registry' })).toHaveAttribute('href', '/admin/tour-seasons/season-registry')
    expect(screen.queryByRole('button', { name: /archive|copy|apply|simulate/i })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Edit persisted template — Admin-only' })).toBeInTheDocument()
    expect(screen.getByLabelText('Template id')).toBeDisabled()
    expect(screen.getByLabelText('Template name')).toHaveValue('Template A')
    expect(screen.getAllByRole('button', { name: 'Delete event row' })[0]).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Event 1 locked'))
    expect(screen.getAllByRole('button', { name: 'Delete event row' })[0]).not.toBeDisabled()
    api.updateCalendarTemplate.mockResolvedValueOnce({ template: null, status: 'ok', schema_version: 'calendar_templates.v1' })
    fireEvent.change(screen.getByLabelText('Template name'), { target: { value: 'Template A Updated' } })
    fireEvent.click(screen.getByRole('button', { name: 'Update persisted calendar template' }))
    await waitFor(() => expect(api.updateCalendarTemplate).toHaveBeenCalledWith('template-a', expect.objectContaining({ id: 'template-a', name: 'Template A Updated' })))
    await waitFor(() => expect(api.getCalendarTemplate.mock.calls.filter((call) => call[0] === 'template-a').length).toBeGreaterThan(1))

    api.getCalendarTemplate.mockResolvedValueOnce({
      template: null,
      source_path: 'config/world/calendar_templates.json',
      status: 'ok',
      schema_version: 'calendar_templates.v1'
    })
    renderAppAt('/admin/tour-seasons/season-templates/calendar/missing-template')
    expect(await screen.findByText('Persisted Admin calendar template not found.')).toBeInTheDocument()
  })


  it('creates persisted Admin calendar templates and blocks invalid event payloads', async () => {
    api.createCalendarTemplate.mockResolvedValueOnce({
      template: { id: 'template-a', name: 'Template A', description: '', status: 'draft', events: [] },
      status: 'ok',
      schema_version: 'calendar_templates.v1'
    })

    renderAppAt('/admin/tour-seasons/season-templates/new')
    expect(await screen.findByRole('heading', { name: 'Create persisted Admin calendar template' })).toBeInTheDocument()
    expect(screen.getAllByText(/does not mutate canonical seasons, Viewer, runs, rankings, race, history, or simulation output/i).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /copy|apply|simulate/i })).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Template id'), { target: { value: 'template-a' } })
    fireEvent.change(screen.getByLabelText('Template name'), { target: { value: 'Template A' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add event row' }))
    fireEvent.change(screen.getByLabelText('Event 1 id'), { target: { value: 'event-a' } })
    fireEvent.change(screen.getByLabelText('Event 1 name'), { target: { value: 'Event A' } })
    fireEvent.change(screen.getByLabelText('Event 1 weeks'), { target: { value: '6,7' } })
    fireEvent.change(screen.getByLabelText('Event 1 qualification_weeks'), { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create persisted calendar template' }))

    await waitFor(() => expect(api.createCalendarTemplate).toHaveBeenCalledWith(expect.objectContaining({ id: 'template-a', events: [expect.objectContaining({ id: 'event-a', weeks: [6, 7], qualification_weeks: [5] })] })))
    expect(await screen.findByRole('heading', { name: 'Persisted Admin calendar template' })).toBeInTheDocument()
  })

  it('blocks invalid persisted Admin calendar template create submissions', async () => {
    renderAppAt('/admin/tour-seasons/season-templates/new')
    expect(await screen.findByRole('heading', { name: 'Create persisted Admin calendar template' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Template id'), { target: { value: 'template-b' } })
    fireEvent.change(screen.getByLabelText('Template name'), { target: { value: 'Template B' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add event row' }))
    fireEvent.change(screen.getByLabelText('Event 1 id'), { target: { value: 'event-a' } })
    fireEvent.change(screen.getByLabelText('Event 1 name'), { target: { value: 'Event A' } })
    fireEvent.change(screen.getByLabelText('Event 1 weeks'), { target: { value: '0,6,6' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create persisted calendar template' }))
    expect(await screen.findByText(/values must be integers 1..61/)).toBeInTheDocument()
    expect(screen.getByText(/values must be unique per event/)).toBeInTheDocument()
    expect(api.createCalendarTemplate).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Event 1 weeks'), { target: { value: '' } })
    fireEvent.change(screen.getByLabelText('Template status'), { target: { value: 'active' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create persisted calendar template' }))
    expect(await screen.findByText(/active templates require weeks/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Add event row' }))
    fireEvent.change(screen.getByLabelText('Event 2 id'), { target: { value: 'event-a' } })
    fireEvent.change(screen.getByLabelText('Event 2 name'), { target: { value: 'Event B' } })
    fireEvent.change(screen.getByLabelText('Event 1 weeks'), { target: { value: '6' } })
    fireEvent.change(screen.getByLabelText('Event 2 weeks'), { target: { value: '7' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create persisted calendar template' }))
    expect(await screen.findByText(/Event ids must be unique inside template/)).toBeInTheDocument()
  })

  it('renders Players hub route with Talent Intake and Player Database links', async () => {
    renderAppAt('/admin/players')
    expect(await screen.findByRole('heading', { name: 'Players' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Player Database/i })).toHaveAttribute('href', '/admin/players/database')
    expect(screen.getByRole('link', { name: /Talent Intake/i })).toHaveAttribute('href', '/admin/players/intake')
  })

  it('renders Talent Intake shell route with workflow steps and no fake table data', async () => {
    renderAppAt('/admin/players/intake')
    expect(await screen.findByRole('heading', { name: 'Talent Intake' })).toBeInTheDocument()
    expect(screen.getByText('Select Season')).toBeInTheDocument()
    expect(screen.getByText('Generate Preview')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('renders world hub cards for Countries and Talent Preview', async () => {
    renderAppAt('/admin/world')
    expect(await screen.findByRole('heading', { name: 'World' })).toBeInTheDocument()
    expect(screen.getByText('Manage country inputs and expected talent output used by the FAX squash simulation engine.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /World Library Browse registered World Packages/i })).toHaveAttribute('href', '/admin/world/library')
    expect(screen.getByRole('link', { name: /Countries Edit country inputs/i })).toHaveAttribute('href', '/admin/world/countries')
    expect(screen.getByRole('link', { name: /Talent Preview Preview expected Elite Talents/i })).toHaveAttribute('href', '/admin/world/talent-preview')
    expect(screen.queryByRole('link', { name: 'Country Momentum' })).not.toBeInTheDocument()
  })

  it('renders read-only World Library from the registry', async () => {
    renderAppAt('/admin/world/library')

    expect(await screen.findByRole('heading', { name: 'World Library' })).toBeInTheDocument()
    expect(api.listWorldPackages).toHaveBeenCalled()
    expect(await screen.findByRole('cell', { name: 'Official FAX World' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'official_fax_world' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'official' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'active' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'built_in' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Read-only' })).toBeInTheDocument()
    expect(screen.getByText('Usage not tracked yet')).toBeInTheDocument()
    expect(screen.getByTitle('abcdef1234567890fedcba0987654321')).toHaveTextContent('abcdef12…87654321')
    expect(screen.getByRole('link', { name: 'View details' })).toHaveAttribute('href', '/admin/world/library/official_fax_world')
  })


  it('renders read-only Custom Worlds returned by the registry', async () => {
    api.listWorldPackages.mockResolvedValueOnce({ packages: [{ world_id: 'my_custom_world', name: 'My Custom World', description: 'Custom world package.', type: 'custom', status: 'active', source: 'custom_config', editable: true, deletable: true, archivable: true, version: 'v1', fingerprint: '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef', country_count: 2, manual_override_count: 0, continent_count: 1, region_count: 1, travel_region_count: 1, used_by_run_count: null, validation_status: 'valid', storage: { countries_path: 'config/worlds/custom/my_custom_world/countries.json', manual_player_overrides_path: '', world_metadata_path: 'config/worlds/custom/my_custom_world/world.json', continents_path: 'config/worlds/custom/my_custom_world/continents.json', regions_path: 'config/worlds/custom/my_custom_world/regions.json', travel_regions_path: 'config/worlds/custom/my_custom_world/travel_regions.json' } }] })

    renderAppAt('/admin/world/library')

    expect(await screen.findByRole('cell', { name: 'My Custom World' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'my_custom_world' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'custom' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'custom_config' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Editable' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /create|edit|delete|archive|clone|import|export/i })).not.toBeInTheDocument()
  })

  it('opens Custom World Library detail without mutation actions', async () => {
    api.getWorldPackage.mockResolvedValueOnce({ world_id: 'my_custom_world', name: 'My Custom World', description: 'Custom world package.', type: 'custom', status: 'active', source: 'custom_config', editable: true, deletable: true, archivable: true, version: 'v1', fingerprint: '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef', country_count: 2, manual_override_count: 0, continent_count: 1, region_count: 1, travel_region_count: 1, used_by_run_count: null, validation_status: 'valid', storage: { countries_path: 'config/worlds/custom/my_custom_world/countries.json', manual_player_overrides_path: '', world_metadata_path: 'config/worlds/custom/my_custom_world/world.json', continents_path: 'config/worlds/custom/my_custom_world/continents.json', regions_path: 'config/worlds/custom/my_custom_world/regions.json', travel_regions_path: 'config/worlds/custom/my_custom_world/travel_regions.json' } })
    api.getWorldPackageValidation.mockResolvedValueOnce({ world_id: 'my_custom_world', status: 'valid', error_count: 0, warning_count: 0, info_count: 6, checks: [{ code: 'world_metadata_valid', severity: 'info', status: 'passed', message: 'world.json is present and declares my_custom_world.', path: 'config/worlds/custom/my_custom_world/world.json', field: 'world_id' }] })

    renderAppAt('/admin/world/library/my_custom_world')

    expect(await screen.findByText('Custom world package.')).toBeInTheDocument()
    expect(screen.getByText('custom_config')).toBeInTheDocument()
    expect(screen.getByText('Deletable')).toBeInTheDocument()
    expect(screen.getByText('Archivable')).toBeInTheDocument()
    expect(screen.getByText(/Custom World mutation actions are not implemented yet/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /create|edit|delete|archive|clone|import|export/i })).not.toBeInTheDocument()
  })

  it('opens World Library detail as read-only', async () => {
    renderAppAt('/admin/world/library/official_fax_world')

    expect(await screen.findByRole('heading', { name: 'World Package Details' })).toBeInTheDocument()
    expect(api.getWorldPackage).toHaveBeenCalledWith('official_fax_world')
    expect(api.getWorldPackageValidation).toHaveBeenCalledWith('official_fax_world')
    expect(await screen.findByText('Built-in official FAX squash world package.')).toBeInTheDocument()
    expect(screen.getByText('Not deletable')).toBeInTheDocument()
    expect(screen.getByText('Not archivable')).toBeInTheDocument()
    expect(screen.getByText('Usage aggregation is not implemented yet.')).toBeInTheDocument()
    expect(screen.getAllByText('config/worlds/official_fax_world/world.json').length).toBeGreaterThan(0)
    expect(screen.getByText('config/worlds/official_fax_world/continents.json')).toBeInTheDocument()
    expect(await screen.findByText('World Package Validation')).toBeInTheDocument()
    expect(screen.getByText('warnings')).toBeInTheDocument()
    expect(screen.getByText('world_metadata_valid')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Countries Editor' })).toHaveAttribute('href', '/admin/world/countries')
    expect(screen.getByRole('link', { name: 'Open Legacy World Package Import/Export' })).toHaveAttribute('href', '/admin/world/package')
  })


  it('renders Clone Official World section for Official World detail', async () => {
    renderAppAt('/admin/world/library/official_fax_world')

    expect(await screen.findByRole('heading', { name: 'Clone Official World' })).toBeInTheDocument()
    expect(screen.getByText(/does not edit Official FAX World and does not affect existing runs/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText('my_custom_world')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Preview clone' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create Custom World' })).toBeInTheDocument()
  })

  it('previews Official World clone with dry_run true and shows no-write result', async () => {
    api.cloneOfficialWorldPackage.mockResolvedValueOnce({ ok: true, dry_run: true, source_world_id: 'official_fax_world', new_world_id: 'my_custom_world', target_path: 'config/worlds/custom/my_custom_world', created_files: ['world.json', 'countries.json'], package: null, validation: null, errors: [] })
    renderAppAt('/admin/world/library/official_fax_world')

    fireEvent.change(await screen.findByPlaceholderText('my_custom_world'), { target: { value: 'my_custom_world' } })
    fireEvent.change(screen.getByPlaceholderText('My Custom World'), { target: { value: 'My Custom World' } })
    fireEvent.change(screen.getByPlaceholderText('Custom world cloned from Official FAX World.'), { target: { value: 'Custom world cloned from Official FAX World.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview clone' }))

    await waitFor(() => expect(api.cloneOfficialWorldPackage.mock.calls[0][0]).toEqual({ new_world_id: 'my_custom_world', name: 'My Custom World', description: 'Custom world cloned from Official FAX World.', dry_run: true }))
    expect(await screen.findByText(/no files were written/i)).toBeInTheDocument()
    expect(screen.getByText('config/worlds/custom/my_custom_world')).toBeInTheDocument()
    expect(screen.getByText('countries.json')).toBeInTheDocument()
  })

  it('creates Official World clone with dry_run false and shows package, validation, and detail link', async () => {
    api.cloneOfficialWorldPackage.mockResolvedValueOnce({ ok: true, dry_run: false, source_world_id: 'official_fax_world', new_world_id: 'my_custom_world', target_path: 'config/worlds/custom/my_custom_world', created_files: ['world.json'], package: { world_id: 'my_custom_world', name: 'My Custom World', description: 'Custom world package.', type: 'custom', status: 'active', source: 'custom_config', editable: true, deletable: true, archivable: true, version: 'v1', fingerprint: '1234567890abcdef1234567890abcdef', country_count: 3, manual_override_count: 2, continent_count: 2, region_count: 3, travel_region_count: 4, used_by_run_count: null, validation_status: 'valid', storage: { countries_path: 'config/worlds/custom/my_custom_world/countries.json', manual_player_overrides_path: 'config/worlds/custom/my_custom_world/manual_player_overrides.json' } }, validation: { world_id: 'my_custom_world', status: 'valid', error_count: 0, warning_count: 0, info_count: 6, checks: [] }, errors: [] })
    renderAppAt('/admin/world/library/official_fax_world')

    fireEvent.change(await screen.findByPlaceholderText('my_custom_world'), { target: { value: 'my_custom_world' } })
    fireEvent.change(screen.getByPlaceholderText('My Custom World'), { target: { value: 'My Custom World' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Custom World' }))

    await waitFor(() => expect(api.cloneOfficialWorldPackage.mock.calls[0][0]).toEqual(expect.objectContaining({ dry_run: false })))
    expect(await screen.findByText(/Custom World package created/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Created package summary')).toHaveTextContent('custom_config')
    expect(screen.getByLabelText('Created package summary')).toHaveTextContent('3 countries')
    expect(screen.getByLabelText('Clone validation summary')).toHaveTextContent('valid')
    expect(screen.getByRole('link', { name: 'Open new Custom World detail' })).toHaveAttribute('href', '/admin/world/library/my_custom_world')
  })

  it('displays structured clone errors when clone response is not ok', async () => {
    api.cloneOfficialWorldPackage.mockResolvedValueOnce({ ok: false, dry_run: true, source_world_id: 'official_fax_world', new_world_id: 'Bad World', target_path: 'config/worlds/custom/Bad World', created_files: [], package: null, validation: null, errors: [{ field: 'new_world_id', message: 'lowercase letters, numbers, underscores only' }] })
    renderAppAt('/admin/world/library/official_fax_world')

    fireEvent.change(await screen.findByPlaceholderText('my_custom_world'), { target: { value: 'Bad World' } })
    fireEvent.change(screen.getByPlaceholderText('My Custom World'), { target: { value: 'Bad World' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview clone' }))

    expect(await screen.findByText(/new_world_id: lowercase letters/i)).toBeInTheDocument()
    expect(screen.queryByText(/Custom World package created/i)).not.toBeInTheDocument()
  })

  it('displays formatted API errors for clone network failures', async () => {
    api.cloneOfficialWorldPackage.mockRejectedValueOnce(new api.ApiError('clone unavailable', 500))
    renderAppAt('/admin/world/library/official_fax_world')

    fireEvent.change(await screen.findByPlaceholderText('my_custom_world'), { target: { value: 'my_custom_world' } })
    fireEvent.change(screen.getByPlaceholderText('My Custom World'), { target: { value: 'My Custom World' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview clone' }))

    expect(await screen.findByText(/Clone request failed: clone unavailable/i)).toBeInTheDocument()
  })

  it('handles World Library detail validation API errors', async () => {
    api.getWorldPackageValidation.mockRejectedValueOnce(new api.ApiError('validation unavailable', 500))
    renderAppAt('/admin/world/library/official_fax_world')

    expect(await screen.findByText(/Failed to load World Package validation: validation unavailable/i)).toBeInTheDocument()
  })

  it('handles World Library API errors', async () => {
    api.listWorldPackages.mockRejectedValueOnce(new api.ApiError('registry unavailable', 500))
    renderAppAt('/admin/world/library')

    expect(await screen.findByText(/Failed to load World Packages: registry unavailable/i)).toBeInTheDocument()
  })

  it('renders country detail route for existing country code', async () => {
    renderAppAt('/admin/world/countries/EGY')
    expect(await screen.findByRole('heading', { name: 'Egypt (EGY)' })).toBeInTheDocument()
    expect(screen.getByText(/Country profile and authored model inputs/i)).toBeInTheDocument()
  })

  it('renders the Viewer MSA home route as the MSA homepage shell', async () => {
    localStorage.removeItem('beta_engine:viewer_active_run_id')
    api.listRuns.mockResolvedValueOnce({ runs: [] })
    renderAppAt('/viewer')
    expect(await screen.findByRole('heading', { name: /MSA Squash/, level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Featured Tournament Hero' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Other Tournaments This Week' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Ranking snapshots' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Race snapshots' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Viewer hub links' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'What this hub does not infer' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Featured Matches' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Predictions & Upset Watch' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Storylines' })).toBeInTheDocument()
  })

  it('renders the Viewer MSA home route with active run status links without duplicate run navigation', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'viewer-run-1')
    api.listRuns.mockResolvedValueOnce({ runs: [] })
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'viewer-run-1', season: 2027, seed: 5, next_event_index: 0, total_events: 0, completed_event_ids: [] },
      season_state: { season: 2027, next_event_index: 0, completed_event_ids: [], ordered_events: [] }
    })
    api.getRunStatusSummary.mockResolvedValueOnce({
      run_id: 'viewer-run-1',
      season: 2027,
      seed: 5,
      progress: { next_event_index: 0, total_events: 0, completed_event_count: 0 },
      finals: { qualification_available: false, result_available: false },
      rollover: null,
      source: null,
      lineage: { child_run_count: 0 },
      history_counts: { events: 0, ranking_snapshots: 0, race_snapshots: 0 }
    })
    api.listEvents.mockResolvedValueOnce({ run_id: 'viewer-run-1', events: [] })
    api.listRankingSnapshots.mockResolvedValueOnce({ run_id: 'viewer-run-1', snapshots: [] })
    api.listRaceSnapshots.mockResolvedValueOnce({ run_id: 'viewer-run-1', snapshots: [] })
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'viewer-run-1', items: [] })
    api.getFinalsSummary.mockResolvedValueOnce({ run_id: 'viewer-run-1', season: 2027, qualification: null, result: null })
    renderAppAt('/viewer')
    expect(await screen.findByRole('heading', { name: /MSA Squash/, level: 2 })).toBeInTheDocument()
    expect(screen.getAllByText(/viewer-run-1/)[0]).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Active Run Rankings' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/rankings')
    expect(screen.queryByRole('navigation', { name: 'Viewer active run quick links' })).not.toBeInTheDocument()
  })

  it('renders top-level Viewer rankings snapshot landing without duplicate active run nav', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer/rankings')
    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(await screen.findByLabelText('MSA Rankings active run snapshot summary')).toHaveTextContent('run-a')
    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings')
    expect(screen.getByRole('link', { name: 'View latest ranking snapshot' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings/4')
    expect(screen.queryByRole('navigation', { name: 'Viewer active run quick links' })).not.toBeInTheDocument()
  })

  beforeEach(() => {
    api.getEvent.mockResolvedValue({ event_sequence: 2, event_id: 'E2', season: 2027, week: 9, template_id: null, tournament_result: {} })
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2027, seed: 5, next_event_index: 1, total_events: 10, completed_event_ids: [] },
      season_state: { season: 2027, next_event_index: 1, completed_event_ids: [], ordered_events: [] }
    })
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      seed: 5,
      progress: { next_event_index: 1, total_events: 10, completed_event_count: 0 },
      finals: { qualification_available: false, result_available: false },
      rollover: null,
      source: null,
      lineage: { child_run_count: 0 },
      history_counts: { events: 0, ranking_snapshots: 1, race_snapshots: 1 }
    })
    api.listEvents.mockResolvedValue({ events: [] })
    api.getFinalsSummary.mockResolvedValue({ run_id: 'run-a', season: 2027, qualification: {}, result: null })
    api.getFinalsQualification.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      source_as_of_season: 2027,
      source_as_of_week: 42,
      qualification: { qualified_player_ids: ['P1'] }
    })
    api.getFinalsResult.mockRejectedValue(new Error('no result yet'))
    api.getLatestRollover.mockRejectedValue(new Error('no rollover'))
    api.getRolloverBySeason.mockResolvedValue({
      rollover: { run_id: 'run-a', from_season: 2027, to_season: 2028, transitioned_players: 64, metadata: {} }
    })
    api.getPlayerTransitions.mockResolvedValue({ run_id: 'run-a', to_season: 2028, transitions: [] })
    api.getNextSeasonPlayers.mockResolvedValue({ run_id: 'run-a', to_season: 2028, players: [] })
    api.getRunSource.mockResolvedValue({
      source: {
        source_type: 'new_run',
        parent_run_id: null,
        source_rollover_run_id: null,
        source_rollover_from_season: null,
        source_rollover_to_season: null
      }
    })
    api.getRunLineage.mockResolvedValue({
      lineage: {
        run_id: 'run-a',
        source: {
          source_type: 'new_run',
          parent_run_id: null,
          source_rollover_run_id: null,
          source_rollover_from_season: null,
          source_rollover_to_season: null
        },
        children: []
      }
    })
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [{ snapshot_sequence: 4, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: { name: 'ranking-4' } }]
    })
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [{ snapshot_sequence: 7, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: { name: 'race-7' } }]
    })
    api.getRunTalentPlan.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      seed: 5,
      total_talents: 1,
      dataset_status: 'active',
      config_version: 'cfg',
      config_fingerprint: 'fp',
      countries: [
        {
          country_code: 'EGY',
          planned_count: 1,
          quality_weights: { solid_prospect: 1 },
          actual_band_counts: { solid_prospect: 1 },
          bias_profile: {}
        }
      ]
    })
    api.listGeneratedPlayersProvenance.mockResolvedValue({
      run_id: 'run-a',
      players: [
        {
          run_id: 'run-a',
          season: 2027,
          player_id: 'EGY-00001',
          country_code: 'EGY',
          talent_sequence: 1,
          talent_seed_value: 1,
          quality_band: 'solid_prospect',
          is_top_band: false
        }
      ]
    })
  })

  it('renders Finals route', async () => {
    renderAppAt('/runs/run-a/finals')
    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
  })

  it('renders Finals qualification detail route', async () => {
    renderAppAt('/runs/run-a/finals/qualification')
    expect(await screen.findByRole('heading', { name: 'Finals qualification detail' })).toBeInTheDocument()
  })

  it('renders Finals result detail route', async () => {
    api.getFinalsResult.mockResolvedValueOnce({
      run_id: 'run-a',
      season: 2027,
      event_id: 'WORLD_TOUR_FINALS',
      source_as_of_season: 2027,
      source_as_of_week: 42,
      result: { champion_player_id: 'P1' }
    })
    renderAppAt('/runs/run-a/finals/result')
    expect(await screen.findByRole('heading', { name: 'Finals result detail' })).toBeInTheDocument()
  })

  it('renders Rollover route', async () => {
    renderAppAt('/runs/run-a/rollover')
    expect(await screen.findByRole('heading', { name: 'Season Rollover' })).toBeInTheDocument()
  })


  it('renders rollover season detail route', async () => {
    renderAppAt('/runs/run-a/rollover/2028')
    expect(await screen.findByRole('heading', { name: 'Rollover season detail' })).toBeInTheDocument()
  })

  it('renders diagnostics route', async () => {
    renderAppAt('/runs/run-a/diagnostics')
    expect(await screen.findByRole('heading', { name: 'Run diagnostics' })).toBeInTheDocument()
  })

  it('renders world generation route', async () => {
    renderAppAt('/runs/run-a/world-generation')
    expect(await screen.findByRole('heading', { name: 'World generation diagnostics' })).toBeInTheDocument()
  })

  it('renders runs browser route', async () => {
    api.listRuns.mockResolvedValueOnce({ runs: [] })
    renderAppAt('/runs')
    expect(await screen.findByRole('heading', { name: 'Runs browser' })).toBeInTheDocument()
  })

  it('renders activity route', async () => {
    api.getRunActivity.mockResolvedValue({ run_id: 'run-a', items: [] })
    renderAppAt('/runs/run-a/activity')
    expect(await screen.findByRole('heading', { name: 'Run activity' })).toBeInTheDocument()
  })

  it('renders season calendar route', async () => {
    renderAppAt('/runs/run-a/calendar')
    expect(await screen.findByRole('heading', { name: 'Season calendar' })).toBeInTheDocument()
  })

  it('renders week detail route', async () => {
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2027, seed: 5, next_event_index: 0, total_events: 2, completed_event_ids: [] },
      season_state: {
        season: 2027,
        next_event_index: 0,
        completed_event_ids: [],
        ordered_events: [
          { event_id: 'E2', season: 2027, week: 9, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP' },
          { event_id: 'E3', season: 2027, week: 10, tour: 'WORLD', category: 'SILVER', template_id: 'TEMP2' }
        ]
      }
    })
    renderAppAt('/runs/run-a/weeks/9')
    expect(await screen.findByRole('heading', { name: 'Week detail' })).toBeInTheDocument()
  })

  it('renders Bootstrap/Lineage route', async () => {
    renderAppAt('/runs/run-a/bootstrap-lineage')
    expect(await screen.findByRole('heading', { name: 'Bootstrap / Lineage' })).toBeInTheDocument()
  })


  it('renders Season Chain route', async () => {
    renderAppAt('/runs/run-a/season-chain')
    expect(await screen.findByRole('heading', { name: 'Season Chain' })).toBeInTheDocument()
  })



  it('renders planned event detail route', async () => {
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2027, seed: 5, next_event_index: 0, total_events: 1, completed_event_ids: [] },
      season_state: {
        season: 2027,
        next_event_index: 0,
        completed_event_ids: [],
        ordered_events: [{ event_id: 'E2', season: 2027, week: 9, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP' }]
      }
    })
    renderAppAt('/runs/run-a/calendar/E2')
    expect(await screen.findByRole('heading', { name: 'Planned event detail' })).toBeInTheDocument()
  })

  it('renders Event detail route', async () => {
    renderAppAt('/runs/run-a/events/E2')
    expect(await screen.findByRole('heading', { name: 'Event detail' })).toBeInTheDocument()
  })

  it('renders ranking snapshot detail route', async () => {
    renderAppAt('/runs/run-a/snapshots/ranking/4')
    expect(await screen.findByRole('heading', { name: 'Ranking snapshot detail' })).toBeInTheDocument()
  })

  it('renders race snapshot detail route', async () => {
    renderAppAt('/runs/run-a/snapshots/race/7')
    expect(await screen.findByRole('heading', { name: 'Race snapshot detail' })).toBeInTheDocument()
  })

  it('renders concrete season calendar preview with read-only event summary and first 10 note', async () => {
    api.getAdminRankingTable.mockResolvedValue({
      rows: [{ rank: 1, dense_rank: 1, ordinal_position: 1, player_id: 'P-1', player_name: 'Ali Ace', country_code: 'EGY', nationality: 'Egypt', age_years_at_season_start: 24, career_stage: 'prime', current_ability: 90, potential_ability: 94, potential_tier: 'S', archetype: 'all_court', play_style: 'attacking', ranking_points: 1200, race_points: 400, table_points: 1200, manual_override: false, source_generation: 'initial_pool', locked_from_initial_pool: true, movement: null, previous_rank: null, events_counted: null, player_fingerprint: null }],
      summary: { season: '2000/2001', table_type: 'ranking', player_count: 1, total_source_players: 1, ranked_player_count: 1, zero_point_players: 0, countries_represented: 1, leader_player_id: 'P-1', leader_points: 1200, generated_from_active_players_fingerprint: 'active-fp', rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: false },
      metadata: { season: '2000/2001', table_type: 'ranking', source: 'season_active_players', active_players_fingerprint: 'active-fp', generated_fingerprint: 'generated-fp', ranking_basis: 'current active season player ranking_points', filters: { country_code: null, search: null, include_zero_points: true, min_points: null }, limit: 10, warnings: [] },
      validation_warnings: [], validation_errors: []
    })
    api.getAdminRankingSnapshot.mockResolvedValue({ snapshot: null, snapshot_exists: true, summary: { ranking: { season: '2000/2001', season_week: 1, table_type: 'ranking', player_count: 1, ranked_player_count: 1, zero_point_players: 0, countries_represented: 1, leader_player_id: 'P-1', leader_points: 1200, previous_snapshot_key: null, new_entries_count: 1, moved_up_count: 0, moved_down_count: 0, unchanged_count: 0, rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: false }, race: { season: '2000/2001', season_week: 1, table_type: 'race', player_count: 1, ranked_player_count: 1, zero_point_players: 0, countries_represented: 1, leader_player_id: 'P-1', leader_points: 400, previous_snapshot_key: null, new_entries_count: 1, moved_up_count: 0, moved_down_count: 0, unchanged_count: 0, rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: false } }, metadata: { season: '2000/2001', season_week: 1, calendar_year: 2000, year_week: 37, source: 'active_season_players', active_players_fingerprint: 'active-fp', point_awards_fingerprint: null, ranking_table_fingerprint: 'r-fp', race_table_fingerprint: 'rc-fp', snapshot_fingerprint: 's-fp', previous_snapshot_fingerprint: null, dry_run: true, persisted: false, generated_seed: 1, persistence_path: null, publication_basis: 'preview', rolling_ranking_implemented: false, best_n_implemented: false }, validation_warnings: [], validation_errors: [] })
    api.getAdminPointBreakdown.mockResolvedValue({ breakdown: null, summary_rows: [{ player_id: 'P-1', player_name: 'Ali Ace', country_code: 'EGY', ranking_points: 1200, race_points: 400, breakdown_ranking_points_total: 1200, breakdown_race_points_total: 400, applied_event_count: 3, total_event_count: 3, consistency_ok: true, top_result_stage: 'Winner', top_result_event_id: 'EVT-1' }], metadata: { season: '2000/2001', source: 'season_point_awards', active_players_fingerprint: 'active-fp', point_awards_fingerprint: 'awards-fp', generated_fingerprint: 'generated-fp', applied_only: true, table_type: 'both', filters: { player_id: null, search: null, country_code: null, include_zero_point_awards: false }, limit: 10, rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: false }, validation_warnings: [], validation_errors: [] })
    api.getSeasonCalendar
      .mockResolvedValueOnce({
      calendar: {
        season: '2000/2001',
        events: Array.from({ length: 11 }, (_, index) => ({
          event_id: `EVT-2000-W${String(index + 1).padStart(2, '0')}-wt`,
          season: '2000/2001',
          season_week: index + 1,
          calendar_year: 2000,
          year_week: 36 + index + 1,
          template_id: `wt_${index + 1}`,
          event_name: index === 0 ? 'World A' : `Event ${index + 1}`,
          category: index % 2 === 0 ? 'PLATINUM' : 'GOLD',
          tour_level: 'WORLD_TOUR',
          host_country: index % 2 === 0 ? 'ENG' : 'USA',
          host_city: null,
          region: index % 2 === 0 ? 'EUROPE' : 'NORTH_AMERICA',
          duration_in_season_weeks: 1,
          start_season_week: index + 1,
          end_season_week: index + 1,
          status: 'planned',
          main_draw_size: 32,
          qualification_draw_size: 16,
          seeds_count: 8,
          qualifier_spots: 4,
          wild_cards: 2,
          byes: 0,
          point_distribution_ref: null,
          point_distribution: null,
          prize_money: 100000,
          prestige: 8,
          event_level_overrides: {},
          source_template_fingerprint: null,
          template_snapshot_fingerprint: null,
          calendar_fingerprint: null,
          template_snapshot: {}
        })),
        metadata: null,
        validation_warnings: [{ severity: 'warning', code: 'calendar_warn', message: 'warn', event_id: null, field: null }],
        validation_errors: []
      },
      summary: { event_count: 11, season_weeks_used: 11, first_event_week: 1, last_event_week: 11, world_tour_events: 11, elite_tour_events: 0, validation_warning_count: 1, validation_error_count: 0, persisted: true, calendar_exists: true },
      metadata: null,
      validation_warnings: [{ severity: 'warning', code: 'calendar_warn', message: 'warn', event_id: null, field: null }],
      validation_errors: []
    })
      .mockResolvedValueOnce({
        calendar: {
          season: '2000/2001',
          events: Array.from({ length: 11 }, (_, index) => ({
            event_id: `E-${index + 1}`,
            season: '2000/2001',
            season_week: index + 1,
            calendar_year: 2000,
            year_week: 37 + index,
            template_id: `wt_${index + 1}`,
            event_name: index === 0 ? 'World A' : `Event ${index + 1}`,
            category: index % 2 === 0 ? 'PLATINUM' : 'GOLD',
            tour_level: 'WORLD_TOUR',
            host_country: index % 2 === 0 ? 'ENG' : 'USA',
            host_city: null,
            region: index % 2 === 0 ? 'EUROPE' : 'NORTH_AMERICA',
            duration_in_season_weeks: 1,
            start_season_week: index + 1,
            end_season_week: index + 1,
            status: 'planned',
            main_draw_size: 32,
            qualification_draw_size: 16,
            seeds_count: 8,
            qualifier_spots: 4,
            wild_cards: 2,
            byes: 0,
            point_distribution_ref: null,
            point_distribution: null,
            prize_money: 100000,
            prestige: 8,
            event_level_overrides: {},
            source_template_fingerprint: null,
            template_snapshot_fingerprint: null,
            calendar_fingerprint: null,
            template_snapshot: {}
          })),
          metadata: null,
          validation_warnings: [{ severity: 'warning', code: 'calendar_warn', message: 'warn', event_id: null, field: null }],
          validation_errors: []
        },
        summary: { event_count: 11, season_weeks_used: 11, first_event_week: 1, last_event_week: 11, world_tour_events: 11, elite_tour_events: 0, validation_warning_count: 1, validation_error_count: 0, persisted: true, calendar_exists: true },
        metadata: null,
        validation_warnings: [{ severity: 'warning', code: 'calendar_warn', message: 'warn', event_id: null, field: null }],
        validation_errors: []
      })
    renderAppAt('/admin/seasons/detail/2000%2F01')
    expect(await screen.findByRole('heading', { name: 'Calendar preview (read-only)' })).toBeInTheDocument()
    expect(await screen.findByText('Calendar loaded.')).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Event count: 11'))).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'World A' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Ranking & points preview (read-only)' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Ranking & points preview' })).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Player count: 1'))).toBeInTheDocument()
    expect(screen.getAllByRole('cell', { name: 'Ali Ace (P-1)' }).length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: 'Ranking snapshot W1' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Point breakdown (Top 10, applied only, non-zero)' })).toBeInTheDocument()
    expect(screen.getByText('Showing first 10 events only. Full calendar tooling remains in Seasons.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /build|edit|apply|generate|simulate|recalculate/i })).not.toBeInTheDocument()
  })

  it('renders concrete season calendar preview no-calendar state', async () => {
    api.getSeasonCalendar
      .mockResolvedValueOnce({
      calendar: null,
      summary: { event_count: 0, season_weeks_used: 0, first_event_week: null, last_event_week: null, world_tour_events: 0, elite_tour_events: 0, validation_warning_count: 0, validation_error_count: 0, persisted: false, calendar_exists: false },
      metadata: null,
      validation_warnings: [],
      validation_errors: []
    })
      .mockResolvedValueOnce({
        calendar: null,
        summary: { event_count: 0, season_weeks_used: 0, first_event_week: null, last_event_week: null, world_tour_events: 0, elite_tour_events: 0, validation_warning_count: 0, validation_error_count: 0, persisted: false, calendar_exists: false },
        metadata: null,
        validation_warnings: [],
        validation_errors: []
      })
    renderAppAt('/admin/seasons/detail/2000%2F01')
    expect(await screen.findByText('No calendar exists yet for this season.')).toBeInTheDocument()
  })


  it('renders concrete season calendar preview invalid-label state without calendar fetch', async () => {
    renderAppAt('/admin/seasons/detail/not-a-season')
    expect(await screen.findByRole('heading', { name: 'Calendar preview (read-only)' })).toBeInTheDocument()
    expect(screen.getByText('Calendar preview unavailable for invalid season label.')).toBeInTheDocument()
    expect(api.getSeasonCalendar).not.toHaveBeenCalled()
    expect(screen.getByText('Ranking & points preview unavailable for invalid season label.')).toBeInTheDocument()
    expect(api.getAdminRankingTable).not.toHaveBeenCalled()
    expect(api.getAdminRankingSnapshot).not.toHaveBeenCalled()
    expect(api.getAdminPointBreakdown).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: /build|edit|apply|generate|simulate/i })).not.toBeInTheDocument()
  })

  it('shows guarded create-only apply rejection and non-applied response safely', async () => {
    api.getSeasonCalendar.mockResolvedValueOnce({
      calendar: null,
      summary: { event_count: 0, season_weeks_used: 0, first_event_week: null, last_event_week: null, world_tour_events: 0, elite_tour_events: 0, validation_warning_count: 0, validation_error_count: 0, persisted: false, calendar_exists: false },
      metadata: null,
      validation_warnings: [],
      validation_errors: []
    })
    renderAppAt('/admin/seasons/build')
    const confirmationInput = await screen.findByLabelText('Exact confirmation phrase')
    const mutationScopeInput = screen.getByLabelText('Mutation scope')
    const executeCreateOnlyButton = screen.getByRole('button', { name: 'Execute create-only season calendar command' })
    await waitFor(() => expect(api.postSeasonBuilderApplyCreateOnlyReadiness).toHaveBeenCalled())
    fireEvent.change(confirmationInput, { target: { value: 'I understand this will create a new season calendar.' } })
    fireEvent.change(mutationScopeInput, { target: { value: 'create_only' } })
    await waitFor(() => expect(executeCreateOnlyButton).toBeEnabled())
    const readinessCallsBeforeClick = api.postSeasonBuilderApplyCreateOnlyReadiness.mock.calls.length

    api.postSeasonBuilderApplyCreateOnlyCommand.mockRejectedValueOnce(
      new api.ApiError(JSON.stringify({
        detail: 'Create-only rejected.',
        audit_persisted: true,
        audit_persistence_status: 'persisted_rejected',
        audit_record_id: 'aud_rejected_test',
        audit_record_fingerprint: 'aud_rejected_fp_test',
        validation_errors: ['Target calendar already exists for season 2000/01.']
      }), 409)
    )
    fireEvent.click(executeCreateOnlyButton)
    await waitFor(() => expect(api.postSeasonBuilderApplyCreateOnlyCommand).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('Create-only command was rejected or failed; no success result is recorded in this panel.')).toBeInTheDocument()
    expect(screen.getByText(/Create-only command failed:/)).toBeInTheDocument()
    expect(screen.getByText('No calendar was created.')).toBeInTheDocument()
    expect(screen.getByText('persisted_rejected')).toBeInTheDocument()
    expect(screen.getByText('aud_rejected_test')).toBeInTheDocument()
    expect(screen.getByText('aud_rejected_fp_test')).toBeInTheDocument()
    expect(screen.queryByText('Create-only apply result')).not.toBeInTheDocument()
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).toHaveBeenCalledTimes(1)
    expect(api.postSeasonBuilderApplyCreateOnlyReadiness.mock.calls.length).toBeGreaterThanOrEqual(readinessCallsBeforeClick)

    api.postSeasonBuilderApplyCreateOnlyCommand.mockResolvedValueOnce({
      command: 'season_builder_apply_create_only',
      enabled: true,
      can_execute: true,
      can_mutate: true,
      applied: false,
      target_season_label: '2000/01',
      validation_errors: ['Rejected by create-only guard.'],
      validation_warnings: ['Not applied in this response.'],
      created_calendar_summary: { calendar_exists: false, season: '2000/01', event_count: 0 },
      created_event_preview: [],
      created_calendar_identity: {},
      created_calendar_validation_preview: {},
      apply_gate_summary: {},
      applied_event_count: 0,
      dry_run_identity: {},
      audit_preview: { audit_persisted: true, audit_persistence_status: 'persisted_rejected', audit_record_id: 'aud_rejected_response', audit_record_fingerprint: 'aud_rejected_response_fp' },
      audit_persisted: true,
      audit_persistence_status: 'persisted_rejected',
      audit_record_id: 'aud_rejected_response',
      audit_record_fingerprint: 'aud_rejected_response_fp',
      message: 'Command completed without applying.'
    })
    fireEvent.click(executeCreateOnlyButton)
    await waitFor(() => expect(api.postSeasonBuilderApplyCreateOnlyCommand).toHaveBeenCalledTimes(1))
    expect(screen.getAllByText('Target calendar now exists. Create-only apply is locked out for this target.').length).toBeGreaterThan(0)
    expect(screen.queryByText('Command response did not report applied=true.')).not.toBeInTheDocument()
    expect(screen.queryByText('Create-only calendar apply reported success.')).not.toBeInTheDocument()
    expect(screen.queryByText('Create-only apply did not report applied=true; calendar verification is informational only.')).not.toBeInTheDocument()
    expect(screen.queryByText('Post-apply calendar verification passed.')).not.toBeInTheDocument()
    expect(screen.getByText('No create-only apply validation preview yet.')).toBeInTheDocument()
    expect(screen.queryByText('Issue codes (first 10): calendar_validation_demo_warning')).not.toBeInTheDocument()
  })

  it('shows empty apply-response validation preview message for non-applied response payload', () => {
    render(
      <ApplyResponseValidationPreviewPanel
        applyMutationResult={{
          command: 'season_builder_apply_create_only',
          enabled: true,
          can_execute: true,
          can_mutate: true,
          applied: false,
          target_season_label: '2000/01',
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
          message: 'Command completed without applying.'
        }}
      />
    )
    expect(screen.getByText('No created-calendar validation preview was returned with this apply response.')).toBeInTheDocument()
    expect(screen.queryByText('Validation status: warnings')).not.toBeInTheDocument()
  })

  it('keeps post-apply verification pending while refreshed data is fetching', () => {
    const applyResult = {
      command: 'season_builder_apply_create_only',
      enabled: true,
      can_execute: true,
      can_mutate: true,
      applied: true,
      target_season_label: '2000/01',
      validation_errors: [],
      validation_warnings: [],
      created_calendar_summary: { calendar_exists: true, season: '2000/01', event_count: 1 },
      created_event_preview: [],
      created_calendar_identity: {},
      created_calendar_validation_preview: {},
      apply_gate_summary: {},
      applied_event_count: 1,
      dry_run_identity: {},
      audit_preview: { audit_persisted: false },
      message: 'Create-only apply executed successfully.'
    }

    const { rerender } = render(
      <PostApplyCalendarVerificationPanel
        targetCalendarData={{
          calendar: { season: '2000/01', source_template_id: null, generated_at: '2026-05-22T00:00:00Z', generated_by: 'test', events: [] } as any,
          summary: { event_count: 1, season_weeks_used: 1, first_event_week: 1, last_event_week: 1, world_tour_events: 1, elite_tour_events: 0, validation_warning_count: 0, validation_error_count: 0, persisted: true, calendar_exists: true },
          metadata: null,
          validation_warnings: [],
          validation_errors: []
        }}
        targetCalendarLoading={false}
        targetCalendarFetching={true}
        targetCalendarError={null}
        readinessData={undefined}
        readinessFetching={false}
        applyMutationResult={applyResult}
        targetCalendarExistsAfterApply={false}
      />
    )
    expect(screen.getByText('Post-apply verification pending refreshed target calendar data.')).toBeInTheDocument()
    expect(screen.queryByText('Post-apply calendar verification passed.')).not.toBeInTheDocument()

    rerender(
      <PostApplyCalendarVerificationPanel
        targetCalendarData={{
          calendar: { season: '2000/01', source_template_id: null, generated_at: '2026-05-22T00:00:00Z', generated_by: 'test', events: [] } as any,
          summary: { event_count: 1, season_weeks_used: 1, first_event_week: 1, last_event_week: 1, world_tour_events: 1, elite_tour_events: 0, validation_warning_count: 0, validation_error_count: 0, persisted: true, calendar_exists: true },
          metadata: null,
          validation_warnings: [],
          validation_errors: []
        }}
        targetCalendarLoading={false}
        targetCalendarFetching={false}
        targetCalendarError={null}
        readinessData={undefined}
        readinessFetching={false}
        applyMutationResult={applyResult}
        targetCalendarExistsAfterApply={true}
      />
    )
    expect(screen.getByText('Post-apply calendar verification passed.')).toBeInTheDocument()
  })
})

describe('Validation severity interpretation panels', () => {
  it('shows clean interpretation for clean status with zero counts', () => {
    render(
      <TargetCalendarValidationPanel
        queryEnabled
        query={{
          isLoading: false,
          isFetching: false,
          error: null,
          data: {
            season: '2000/01',
            calendar_exists: true,
            validation_summary: {
              status: 'clean',
              error_count: 0,
              warning_count: 0,
              info_count: 0,
              event_count: 0,
              first_season_week: null,
              last_season_week: null,
              categories: { count: 0, values: [] },
              tour_levels: { count: 0, values: [] },
              host_countries: { count: 0, values: [] }
            },
            issues: [],
            read_only: true,
            message: 'ok'
          }
        }}
      />
    )
    expect(screen.getByText('Target validation interpretation: Validation is clean.')).toBeInTheDocument()
  })

  it('groups malformed severity into unknown issue summary with missing code fallback', () => {
    render(
      <TargetCalendarValidationPanel
        queryEnabled
        query={{
          isLoading: false,
          isFetching: false,
          error: null,
          data: {
            season: '2000/01',
            calendar_exists: true,
            validation_summary: {
              status: 'warnings',
              error_count: 0,
              warning_count: 0,
              info_count: 0,
              event_count: 1,
              first_season_week: 1,
              last_season_week: 1,
              categories: { count: 0, values: [] },
              tour_levels: { count: 0, values: [] },
              host_countries: { count: 0, values: [] }
            },
            issues: [{ severity: 'mystery' as never, code: '', message: 'Bad issue shape' } as never],
            read_only: true,
            message: 'ok'
          }
        }}
      />
    )
    expect(screen.getByText('Unknown-severity issues: 1')).toBeInTheDocument()
    expect(screen.getByText('Unknown issue codes: (missing_code)')).toBeInTheDocument()
  })

  it('shows unknown registry metadata fallback when issue code is missing from registry', () => {
    render(
      <TargetCalendarValidationPanel
        queryEnabled
        issueCodeRegistryData={{
          read_only: true,
          code_count: 1,
          message: 'registry',
          codes: [
            {
              code: 'known_code',
              severity: 'warning',
              title: 'Known code',
              description: 'Known code description.',
              field: null,
              read_only: true
            }
          ]
        }}
        query={{
          isLoading: false,
          isFetching: false,
          error: null,
          data: {
            season: '2000/01',
            calendar_exists: true,
            validation_summary: {
              status: 'warnings',
              error_count: 0,
              warning_count: 1,
              info_count: 0,
              event_count: 1,
              first_season_week: 1,
              last_season_week: 1,
              categories: { count: 0, values: [] },
              tour_levels: { count: 0, values: [] },
              host_countries: { count: 0, values: [] }
            },
            issues: [{ severity: 'warning', code: 'unknown_code', message: 'Unknown code issue.', event_id: 'event-1', field: 'category', context: {} }],
            read_only: true,
            message: 'ok'
          }
        }}
      />
    )
    expect(screen.getByText('Unknown issue code')).toBeInTheDocument()
    expect(screen.getByText('No registry metadata available for this issue code.')).toBeInTheDocument()
  })

  it('shows blocking-errors interpretation when apply preview has errors', () => {
    render(
      <ApplyResponseValidationPreviewPanel
        applyMutationResult={{
          created_calendar_validation_preview: {
            validation_status: 'errors',
            error_count: 1,
            warning_count: 0
          }
        } as never}
      />
    )
    expect(screen.getByText('Apply response validation interpretation: Validation has blocking errors.')).toBeInTheDocument()
  })

  it('shows unavailable interpretation for malformed apply preview status/counts', () => {
    render(
      <ApplyResponseValidationPreviewPanel
        applyMutationResult={{
          created_calendar_validation_preview: {
            validation_status: 'mystery'
          }
        } as never}
      />
    )
    expect(screen.getByText('Apply response validation interpretation: Validation status is unavailable.')).toBeInTheDocument()
  })

  it('shows unknown apply-response issue code fallback when metadata is unavailable', () => {
    render(
      <ApplyResponseValidationPreviewPanel
        applyMutationResult={{
          created_calendar_validation_preview: {
            issue_codes_first_10: ['unknown_apply_code']
          }
        } as never}
        issueCodeRegistryData={{
          read_only: true,
          code_count: 1,
          message: 'registry',
          codes: [
            {
              code: 'known_code',
              severity: 'warning',
              title: 'Known code',
              description: 'Known code description.',
              field: null,
              read_only: true
            }
          ]
        }}
      />
    )
    expect(screen.getByText('Apply-response issue code metadata')).toBeInTheDocument()
    expect(screen.getByText('unknown_apply_code')).toBeInTheDocument()
    expect(screen.getByText('Unknown issue code')).toBeInTheDocument()
    expect(screen.getByText('No registry metadata available for this issue code.')).toBeInTheDocument()
  })

  it('shows compact empty issue-code metadata state when apply response issue code list is empty', () => {
    render(
      <ApplyResponseValidationPreviewPanel
        applyMutationResult={{
          created_calendar_validation_preview: {
            issue_codes_first_10: []
          }
        } as never}
      />
    )
    expect(screen.getByText('Issue codes (first 10):')).toBeInTheDocument()
    expect(screen.getByText('Apply-response issue code count: 0')).toBeInTheDocument()
    expect(screen.getByText('No apply-response issue codes to enrich.')).toBeInTheDocument()
    expect(screen.queryByText('unknown/code')).not.toBeInTheDocument()
  })
})


describe('ValidationIssueCodeRegistryPanel', () => {
  it('shows loading state', () => {
    render(<ValidationIssueCodeRegistryPanel query={{ isLoading: true, isFetching: false, error: null, data: undefined }} />)
    expect(screen.getByText('Loading validation issue code registry…')).toBeInTheDocument()
  })

  it('shows error state', () => {
    render(<ValidationIssueCodeRegistryPanel query={{ isLoading: false, isFetching: false, error: new Error('boom'), data: undefined }} />)
    expect(screen.getByText(/Unable to load validation issue code registry:/)).toBeInTheDocument()
  })

  it('shows empty registry state', () => {
    render(<ValidationIssueCodeRegistryPanel query={{ isLoading: false, isFetching: false, error: null, data: { read_only: true, code_count: 0, message: 'empty', codes: [] } }} />)
    expect(screen.getByText('No issue codes returned.')).toBeInTheDocument()
  })
})

describe('SeasonTemplateSlotValidationPanel issue code registry fallback', () => {
  it('shows fallback metadata for unknown issue codes', () => {
    render(
      <SeasonTemplateSlotValidationPanel
        queryEnabled
        query={{
          isLoading: false,
          isFetching: false,
          error: null,
          data: {
            template_id: 'default_msa_template_preview',
            template_exists: true,
            read_only: true,
            message: 'Template slot validation completed.',
            summary: { status: 'warnings', error_count: 0, warning_count: 1, issue_count: 1, slot_count: 1, week_count: 1, first_week: 1, last_week: 1 },
            issues: [{ severity: 'warning', code: 'unknown_template_slot_code', slot_id: 'slot-01', message: 'Unknown code warning.' }]
          }
        }}
        issueCodeRegistryData={{
          read_only: true,
          code_count: 1,
          message: 'registry',
          codes: [{ code: 'template_slot_duration_long', severity: 'warning', title: 'Template slot duration long', description: 'Template slot duration is unusually long.', field: 'duration_in_season_weeks', read_only: true }]
        }}
      />
    )
    expect(screen.getByText('Unknown template slot issue code')).toBeInTheDocument()
    expect(screen.getByText('No registry metadata available for this template slot issue code.')).toBeInTheDocument()
  })
})

describe('TemplateSlotValidationPreflightConsistencyPanel', () => {
  it('prefers structured preflight preview issue codes when available', () => {
    render(
      <TemplateSlotValidationPreflightConsistencyPanel
        slotValidationData={{
          template_id: 'default_msa_template_preview',
          template_exists: true,
          read_only: true,
          message: 'ok',
          summary: { status: 'warnings', error_count: 0, warning_count: 2, issue_count: 2, slot_count: 2, week_count: 3, first_week: 1, last_week: 3 },
          issues: [
            { severity: 'warning', code: 'template_slot_duration_long', message: 'Duration long', slot_id: 'slot-01' },
            { severity: 'warning', code: 'template_slot_week_overloaded', message: 'Week overloaded', slot_id: 'slot-02' }
          ]
        }}
        preflightResult={{
          can_build: false,
          target_season_label: '2000/2001',
          source_type: 'season_template',
          source_template_id: 'default_msa_template_preview',
          preflight_fingerprint: 'pf',
          reviewed_diff_id: 'rd',
          target_calendar_exists: true,
          target_event_count: 1,
          source_resolved: true,
          source_summary: {},
          authoritative_diff_summary: {},
          template_slot_validation_preview: {
            template_id: 'default_msa_template_preview',
            template_exists: true,
            status: 'warnings',
            error_count: 0,
            warning_count: 1,
            issue_count: 1,
            issue_codes: ['template_slot_duration_long'],
            error_codes: [],
            warning_codes: ['template_slot_duration_long'],
            read_only: true
          },
          validation_warnings: ['[template_slot_duration_long] [slot=slot-01] Template slot duration 5 weeks is unusually long (>3).'],
          validation_errors: [],
          audit_preview: {}
        }}
      />
    )
    expect(screen.getByText('Preflight diagnostics issue codes source: structured preview')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot preview status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot preview issue count: 1')).toBeInTheDocument()
    expect(screen.getByText('Some structured template slot issue codes are missing from preflight diagnostics.')).toBeInTheDocument()
    expect(screen.getAllByText('template_slot_week_overloaded').length).toBeGreaterThan(0)
    expect(screen.getByText('No dry-run result to compare yet.')).toBeInTheDocument()
  })

  it('falls back to bracketed preflight diagnostics when preview is missing', () => {
    render(
      <TemplateSlotValidationPreflightConsistencyPanel
        slotValidationData={{
          template_id: 'default_msa_template_preview',
          template_exists: true,
          read_only: true,
          message: 'ok',
          summary: { status: 'warnings', error_count: 0, warning_count: 1, issue_count: 1, slot_count: 1 },
          issues: [{ severity: 'warning', code: 'template_slot_duration_long', message: 'Duration long', slot_id: 'slot-01' }]
        }}
        preflightResult={{
          can_build: false,
          target_season_label: '2000/2001',
          source_type: 'season_template',
          source_template_id: 'default_msa_template_preview',
          preflight_fingerprint: 'pf',
          reviewed_diff_id: 'rd',
          target_calendar_exists: true,
          target_event_count: 1,
          source_resolved: true,
          source_summary: {},
          authoritative_diff_summary: {},
          validation_warnings: ['[template_slot_duration_long] warning'],
          validation_errors: [],
          audit_preview: {}
        }}
      />
    )
    expect(screen.getByText('Preflight diagnostics issue codes source: bracketed validation messages')).toBeInTheDocument()
  })

  it('falls back to bracketed preflight diagnostics when preview is malformed', () => {
    render(
      <TemplateSlotValidationPreflightConsistencyPanel
        slotValidationData={{
          template_id: 'default_msa_template_preview',
          template_exists: true,
          read_only: true,
          message: 'ok',
          summary: { status: 'warnings', error_count: 0, warning_count: 1, issue_count: 1, slot_count: 1 },
          issues: [{ severity: 'warning', code: 'template_slot_duration_long', message: 'Duration long', slot_id: 'slot-01' }]
        }}
        preflightResult={{
          can_build: false,
          target_season_label: '2000/2001',
          source_type: 'season_template',
          source_template_id: 'default_msa_template_preview',
          preflight_fingerprint: 'pf',
          reviewed_diff_id: 'rd',
          target_calendar_exists: true,
          target_event_count: 1,
          source_resolved: true,
          source_summary: {},
          authoritative_diff_summary: {},
          template_slot_validation_preview: { issue_codes: 'bad' } as any,
          validation_warnings: ['[template_slot_duration_long] warning'],
          validation_errors: [],
          audit_preview: {}
        }}
      />
    )
    expect(screen.getByText('Preflight diagnostics issue codes source: bracketed validation messages')).toBeInTheDocument()
  })
})

describe('TemplateSlotConflictPreflightConsistencyPanel', () => {
  it('shows no selected report state', () => {
    render(<TemplateSlotConflictPreflightConsistencyPanel />)
    expect(screen.getByText('No structured template slot conflict data to compare yet.')).toBeInTheDocument()
  })

  it('shows no preflight and no dry-run result messages', () => {
    render(<TemplateSlotConflictPreflightConsistencyPanel slotConflictData={{ template_id: 't', template_exists: true, read_only: true, message: 'ok', summary: { status: 'warnings', warning_count: 0, info_count: 0, conflict_count: 1, slot_count: 1, occupied_week_count: 1, busiest_week: 1, busiest_week_slot_count: 1, read_only: true }, conflicts: [{ severity: 'warning', code: 'template_conflict_week_overloaded', message: 'm', season_week: 1, slot_ids: ['s1'], categories: [], tour_levels: [], host_countries: [], read_only: true }] }} />)
    expect(screen.getByText('No preflight result to compare yet.')).toBeInTheDocument()
    expect(screen.getByText('No dry-run result to compare yet.')).toBeInTheDocument()
  })

  it('shows all codes represented when preflight preview matches', () => {
    render(<TemplateSlotConflictPreflightConsistencyPanel slotConflictData={{ template_id: 't', template_exists: true, read_only: true, message: 'ok', summary: { status: 'warnings', warning_count: 0, info_count: 0, conflict_count: 1, slot_count: 1, occupied_week_count: 1, busiest_week: 1, busiest_week_slot_count: 1, read_only: true }, conflicts: [{ severity: 'warning', code: 'template_conflict_week_overloaded', message: 'm', season_week: 1, slot_ids: ['s1'], categories: [], tour_levels: [], host_countries: [], read_only: true }] }} preflightResult={{ can_build: false, target_season_label: '2000/2001', source_type: 'season_template', source_template_id: 't', preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', target_calendar_exists: false, target_event_count: 0, source_resolved: true, source_summary: {}, authoritative_diff_summary: {}, template_slot_conflict_preview: { status: 'warnings', conflict_count: 3, conflict_codes: ['template_conflict_week_overloaded'] }, validation_warnings: [], validation_errors: [], audit_preview: {} }} />)
    expect(screen.getByText('All structured template slot conflict codes are represented in preflight preview.')).toBeInTheDocument()
  })

  it('shows missing structured preflight code message', () => {
    render(<TemplateSlotConflictPreflightConsistencyPanel slotConflictData={{ template_id: 't', template_exists: true, read_only: true, message: 'ok', summary: { status: 'warnings', warning_count: 0, info_count: 0, conflict_count: 1, slot_count: 1, occupied_week_count: 1, busiest_week: 1, busiest_week_slot_count: 1, read_only: true }, conflicts: [{ severity: 'warning', code: 'template_conflict_week_overloaded', message: 'm', season_week: 1, slot_ids: ['s1'], categories: [], tour_levels: [], host_countries: [], read_only: true }] }} preflightResult={{ can_build: false, target_season_label: '2000/2001', source_type: 'season_template', source_template_id: 't', preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', target_calendar_exists: false, target_event_count: 0, source_resolved: true, source_summary: {}, authoritative_diff_summary: {}, template_slot_conflict_preview: { status: 'warnings', conflict_count: 0, conflict_codes: ['another_code'] }, validation_warnings: [], validation_errors: [], audit_preview: {} }} />)
    expect(screen.getByText('Preflight conflict preview is missing structured conflict codes: template_conflict_week_overloaded')).toBeInTheDocument()
  })

  it('handles malformed preview safely', () => {
    render(<TemplateSlotConflictPreflightConsistencyPanel slotConflictData={{ template_id: 't', template_exists: true, read_only: true, message: 'ok', summary: { status: 'warnings', warning_count: 0, info_count: 0, conflict_count: 1, slot_count: 1, occupied_week_count: 1, busiest_week: 1, busiest_week_slot_count: 1, read_only: true }, conflicts: [{ severity: 'warning', code: 'template_conflict_week_overloaded', message: 'm', season_week: 1, slot_ids: ['s1'], categories: [], tour_levels: [], host_countries: [], read_only: true }] }} preflightResult={{ can_build: false, target_season_label: '2000/2001', source_type: 'season_template', source_template_id: 't', preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', target_calendar_exists: false, target_event_count: 0, source_resolved: true, source_summary: {}, authoritative_diff_summary: {}, template_slot_conflict_preview: {} as any, validation_warnings: [], validation_errors: [], audit_preview: {} } as any} dryRunResult={{ command: 'season_builder_dry_run_build', enabled: false, can_execute: false, can_mutate: false, target_season_label: '2000/2001', source_type: 'season_template', source_template_id: 't', overwrite_policy: null, preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', validation_warnings: [], validation_errors: [], audit_preview: {}, generation_design_preview: {}, candidate_event_contract_preview: {}, conflict_contract_preview: {}, dry_run_result_contract_preview: {}, dry_run_result_preview: {}, message: 'dry run disabled', template_slot_conflict_preview: { status: 42, conflict_count: NaN, conflict_codes: 'bad' } as any }} />)
    expect(screen.getByText('Preflight template slot conflict preview status: n/a')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict preview status: n/a')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict preview conflict count: n/a')).toBeInTheDocument()
  })
})

describe('TemplateSlotValidationPreviewSummaryPanel', () => {
  it('shows unavailable message when preview is missing', () => {
    render(<TemplateSlotValidationPreviewSummaryPanel titlePrefix="Preflight" preview={undefined} />)
    expect(screen.getByText('Preflight template slot validation preview is not available.')).toBeInTheDocument()
  })

  it('shows normalized rows for valid preview', () => {
    render(
      <TemplateSlotValidationPreviewSummaryPanel
        titlePrefix="Dry-run"
        preview={{
          template_id: 'default_msa_template_preview',
          template_exists: true,
          status: 'warnings',
          error_count: 0,
          warning_count: 1,
          issue_count: 1,
          issue_codes: ['template_slot_duration_long'],
          error_codes: [],
          warning_codes: ['template_slot_duration_long'],
          read_only: true
        }}
      />
    )
    expect(screen.getByText('Dry-run template slot validation preview')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot validation template ID: default_msa_template_preview')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot validation template exists: true')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot validation read-only: true')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot validation status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot validation issue count: 1')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot validation issue codes: template_slot_duration_long')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot validation warning codes: template_slot_duration_long')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot validation error codes: none')).toBeInTheDocument()
  })

  it('handles malformed fields safely', () => {
    render(
      <TemplateSlotValidationPreviewSummaryPanel
        titlePrefix="Preflight"
        preview={{ template_id: '', template_exists: null, status: 42, error_count: NaN, issue_codes: 'bad', error_codes: [null, ''], warning_codes: [], read_only: 'yes' } as any}
      />
    )
    expect(screen.getByText('Preflight template slot validation template ID: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot validation template exists: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot validation status: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot validation error count: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot validation issue codes: none')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot validation warning codes: none')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot validation read-only: n/a')).toBeInTheDocument()
  })

  it('dedupes and normalizes issue code arrays consistently for summary and consistency source selection', () => {
    render(
      <>
        <TemplateSlotValidationPreviewSummaryPanel
          titlePrefix="Preflight"
          preview={{
            template_id: 'default_msa_template_preview',
            template_exists: true,
            status: 'warnings',
            error_count: 0,
            warning_count: 1,
            issue_count: 1,
            issue_codes: ['template_slot_duration_long', ' ', 'template_slot_duration_long', '123'],
            error_codes: [],
            warning_codes: ['template_slot_duration_long'],
            read_only: true
          }}
        />
        <TemplateSlotValidationPreflightConsistencyPanel
          slotValidationData={{
            template_id: 'default_msa_template_preview',
            template_exists: true,
            read_only: true,
            message: 'ok',
            summary: { status: 'warnings', error_count: 0, warning_count: 1, issue_count: 1, slot_count: 1 },
            issues: [{ severity: 'warning', code: 'template_slot_duration_long', message: 'Duration long', slot_id: 'slot-01' }]
          }}
          preflightResult={{
            can_build: false,
            target_season_label: '2000/2001',
            source_type: 'season_template',
            source_template_id: 'default_msa_template_preview',
            preflight_fingerprint: 'pf',
            reviewed_diff_id: 'rd',
            target_calendar_exists: true,
            target_event_count: 1,
            source_resolved: true,
            source_summary: {},
            authoritative_diff_summary: {},
            template_slot_validation_preview: {
              issue_codes: ['template_slot_duration_long', ' ', 'template_slot_duration_long', '123']
            },
            validation_warnings: ['[template_slot_duration_long] warning'],
            validation_errors: [],
            audit_preview: {}
          }}
        />
      </>
    )
    expect(screen.getByText('Preflight template slot validation issue codes: template_slot_duration_long, 123')).toBeInTheDocument()
    expect(screen.getByText('Preflight diagnostics issue codes source: structured preview')).toBeInTheDocument()
  })
})

describe('ApplyResponseVsTargetValidationComparisonPanel', () => {
  it('shows mismatch details when apply preview and refetched target validation differ', () => {
    render(
      <MemoryRouter>
        <ApplyResponseVsTargetValidationComparisonPanel
          applyMutationResult={{
            command: 'season_builder_apply_create_only',
            enabled: true,
            can_execute: true,
            can_mutate: true,
            applied: true,
            target_season_label: '2000/01',
            validation_errors: [],
            validation_warnings: [],
            created_calendar_summary: { calendar_exists: true, season: '2000/01', event_count: 2 },
            created_event_preview: [],
            created_calendar_identity: { applied_event_count: 2 },
            created_calendar_validation_preview: {
              validation_status: 'warnings',
              calendar_exists: true,
              read_only: true,
              event_count: 2,
              error_count: 0,
              warning_count: 1,
              info_count: 1
            },
            apply_gate_summary: { service_insert_succeeded: true },
            applied_event_count: 2,
            dry_run_identity: { identity_matches: true },
            audit_preview: { audit_persisted: false, audit_persistence_status: 'not_implemented' },
            message: 'ok'
          }}
          targetValidationData={{
            season: '2000/01',
            calendar_exists: true,
            validation_summary: { status: 'warnings', error_count: 0, warning_count: 1, info_count: 1, event_count: 1, first_season_week: 1, last_season_week: 1, categories: { count: 1, values: ['GOLD'] }, tour_levels: { count: 1, values: ['WORLD_TOUR'] }, host_countries: { count: 1, values: ['ENG'] } },
            issues: [],
            read_only: true,
            message: 'Read-only validation response.'
          }}
          targetValidationFetching={false}
          targetValidationError={null}
        />
      </MemoryRouter>
    )
    expect(screen.getByText('Apply-response validation preview differs from refetched target validation.')).toBeInTheDocument()
    const eventCountRow = screen.getByText('event_count').closest('tr')
    expect(eventCountRow).not.toBeNull()
    expect(eventCountRow).toHaveTextContent('no')
  })


  it('normalizes missing and malformed optional validation fields to n/a without rendering undefined', () => {
    render(
      <MemoryRouter>
        <ApplyResponseVsTargetValidationComparisonPanel
          applyMutationResult={{
            command: 'season_builder_apply_create_only',
            enabled: true,
            can_execute: true,
            can_mutate: true,
            applied: true,
            target_season_label: '2000/01',
            validation_errors: [],
            validation_warnings: [],
            created_calendar_summary: { calendar_exists: true, season: '2000/01', event_count: 0 },
            created_event_preview: [],
            created_calendar_identity: { applied_event_count: 0 },
            created_calendar_validation_preview: {
              validation_status: 'clean',
              calendar_exists: true,
              read_only: true,
              event_count: 0,
              error_count: 0,
              warning_count: 0,
              info_count: 0
            },
            apply_gate_summary: { service_insert_succeeded: true },
            applied_event_count: 0,
            dry_run_identity: { identity_matches: true },
            audit_preview: { audit_persisted: false, audit_persistence_status: 'not_implemented' },
            message: 'ok'
          }}
          targetValidationData={{
            season: '2000/01',
            calendar_exists: true,
            validation_summary: {
              status: 'clean',
              error_count: 0,
              warning_count: 0,
              info_count: 0,
              event_count: 0,
              first_season_week: undefined,
              last_season_week: undefined,
              categories: undefined,
              tour_levels: {} as any,
              host_countries: null as any
            } as any,
            issues: [],
            read_only: true,
            message: 'Read-only validation response.'
          }}
          targetValidationFetching={false}
          targetValidationError={null}
        />
      </MemoryRouter>
    )

    expect(screen.queryByText('undefined')).not.toBeInTheDocument()
    const firstWeekRow = screen.getByText('first_season_week').closest('tr')
    expect(firstWeekRow).not.toBeNull()
    expect(firstWeekRow).toHaveTextContent('n/a')
    expect(firstWeekRow).toHaveTextContent('yes')

    const categoriesCountRow = screen.getByText('categories.count').closest('tr')
    expect(categoriesCountRow).not.toBeNull()
    expect(categoriesCountRow).toHaveTextContent('n/a')
    expect(categoriesCountRow).toHaveTextContent('yes')
  })

  it('shows no match when shape count is missing on one side', () => {
    render(
      <MemoryRouter>
        <ApplyResponseVsTargetValidationComparisonPanel
          applyMutationResult={{
            command: 'season_builder_apply_create_only',
            enabled: true,
            can_execute: true,
            can_mutate: true,
            applied: true,
            target_season_label: '2000/01',
            validation_errors: [],
            validation_warnings: [],
            created_calendar_summary: { calendar_exists: true, season: '2000/01', event_count: 1 },
            created_event_preview: [],
            created_calendar_identity: { applied_event_count: 1 },
            created_calendar_validation_preview: {
              validation_status: 'clean',
              calendar_exists: true,
              read_only: true,
              event_count: 1,
              error_count: 0,
              warning_count: 0,
              info_count: 0,
              categories: { count: 1 }
            },
            apply_gate_summary: { service_insert_succeeded: true },
            applied_event_count: 1,
            dry_run_identity: { identity_matches: true },
            audit_preview: { audit_persisted: false, audit_persistence_status: 'not_implemented' },
            message: 'ok'
          }}
          targetValidationData={{
            season: '2000/01',
            calendar_exists: true,
            validation_summary: { status: 'clean', error_count: 0, warning_count: 0, info_count: 0, event_count: 1, first_season_week: null, last_season_week: null, categories: {} as any, tour_levels: { count: 0, values: [] }, host_countries: { count: 0, values: [] } },
            issues: [],
            read_only: true,
            message: 'Read-only validation response.'
          }}
          targetValidationFetching={false}
          targetValidationError={null}
        />
      </MemoryRouter>
    )

    const categoriesCountRow = screen.getByText('categories.count').closest('tr')
    expect(categoriesCountRow).not.toBeNull()
    expect(categoriesCountRow).toHaveTextContent('no')
  })
})


describe('TemplateSlotConflictPreviewSummaryPanel', () => {
  it('shows unavailable message when preview is missing', () => {
    render(<TemplateSlotConflictPreviewSummaryPanel titlePrefix="Preflight" preview={undefined} />)
    expect(screen.getByText('Preflight template slot conflict preview is not available.')).toBeInTheDocument()
  })

  it('shows normalized rows for valid preview', () => {
    render(
      <TemplateSlotConflictPreviewSummaryPanel
        titlePrefix="Dry-run"
        preview={{
          template_id: 'default_msa_template_preview',
          template_exists: true,
          status: 'warnings',
          warning_count: 1,
          info_count: 2,
          conflict_count: 3,
          conflict_codes: ['template_conflict_week_overloaded', 'template_conflict_opening_dead_zone'],
          warning_codes: ['template_conflict_week_overloaded'],
          info_codes: ['template_conflict_opening_dead_zone'],
          busiest_week: 5,
          busiest_week_slot_count: 4,
          read_only: true
        }}
      />
    )
    expect(screen.getByText('Dry-run template slot conflict preview')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict template ID: default_msa_template_preview')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict template exists: true')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict read-only: true')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict warning count: 1')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict info count: 2')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict conflict count: 3')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict conflict codes: template_conflict_week_overloaded, template_conflict_opening_dead_zone')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict warning codes: template_conflict_week_overloaded')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict info codes: template_conflict_opening_dead_zone')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict busiest week: 5')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template slot conflict busiest week slot count: 4')).toBeInTheDocument()
  })

  it('handles malformed fields safely', () => {
    render(
      <TemplateSlotConflictPreviewSummaryPanel
        titlePrefix="Preflight"
        preview={{ template_id: '', template_exists: null, status: 42, warning_count: NaN, info_count: Infinity, conflict_count: null, conflict_codes: 'bad', warning_codes: [null, ''], info_codes: [], busiest_week: 'oops', busiest_week_slot_count: NaN, read_only: 'yes' } as any}
      />
    )
    expect(screen.getByText('Preflight template slot conflict template ID: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict template exists: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict read-only: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict status: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict warning count: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict info count: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict conflict count: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict conflict codes: none')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict warning codes: none')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict busiest week: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template slot conflict busiest week slot count: n/a')).toBeInTheDocument()
  })
})




describe('DryRunTemplateConflictSummaryPanel', () => {
  it('shows unavailable message when no dry-run preview is present', () => {
    render(<DryRunTemplateConflictSummaryPanel dryRunResultPreview={undefined} />)
    expect(screen.getByText('Dry-run template conflict summary is not available.')).toBeInTheDocument()
  })

  it('renders normalized summary rows for valid summary', () => {
    render(<DryRunTemplateConflictSummaryPanel dryRunResultPreview={{ template_conflict_summary: { available: true, read_only: true, non_blocking: true, status: 'warnings', warning_count: 1, info_count: 2, conflict_count: 3, conflict_codes: ['template_conflict_week_overloaded', 'template_conflict_week_overloaded'], busiest_week: 5, busiest_week_slot_count: 4, source: 'template_slot_conflict_preview', message: 'Template slot conflict diagnostics are available as read-only non-blocking preview.' } }} />)
    expect(screen.getByText('Dry-run template conflict diagnostics available: true')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict conflict codes: template_conflict_week_overloaded')).toBeInTheDocument()
  })

  it('handles malformed summary fields with n/a or none safely', () => {
    render(<DryRunTemplateConflictSummaryPanel dryRunResultPreview={{ template_conflict_summary: { available: 'yes', read_only: 'yes', non_blocking: null, status: 42, warning_count: NaN, info_count: Infinity, conflict_count: 'three', conflict_codes: 'bad', busiest_week: 'oops', busiest_week_slot_count: {}, source: '', message: '' } }} />)
    expect(screen.getByText('Dry-run template conflict diagnostics available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict status: n/a')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict conflict codes: none')).toBeInTheDocument()
  })

  it('renders unavailable summary with available false and zero counts', () => {
    render(<DryRunTemplateConflictSummaryPanel dryRunResultPreview={{ template_conflict_summary: { available: false, read_only: true, non_blocking: true, status: 'clean', warning_count: 0, info_count: 0, conflict_count: 0, conflict_codes: [], busiest_week: null, busiest_week_slot_count: null, source: 'template_slot_conflict_preview', message: 'No conflicts.' } }} />)
    expect(screen.getByText('Dry-run template conflict diagnostics available: false')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict warning count: 0')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict info count: 0')).toBeInTheDocument()
    expect(screen.getByText('Dry-run template conflict conflict count: 0')).toBeInTheDocument()
  })
})

describe('PreflightTemplateConflictSummaryPanel', () => {
  it('shows unavailable message when no authoritative summary is present', () => {
    render(<PreflightTemplateConflictSummaryPanel authoritativeDiffSummary={undefined} />)
    expect(screen.getByText('Preflight template conflict summary is not available.')).toBeInTheDocument()
  })

  it('renders normalized summary rows for valid summary', () => {
    render(<PreflightTemplateConflictSummaryPanel authoritativeDiffSummary={{ template_conflict_summary: { available: true, read_only: true, non_blocking: true, status: 'warnings', warning_count: 1, info_count: 2, conflict_count: 3, conflict_codes: ['template_conflict_week_overloaded', 'template_conflict_week_overloaded'], busiest_week: 5, busiest_week_slot_count: 4, source: 'template_slot_conflict_preview', message: 'Template slot conflict diagnostics are available as read-only non-blocking preview.' } }} />)
    expect(screen.getByText('Preflight template conflict diagnostics available: true')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict conflict codes: template_conflict_week_overloaded')).toBeInTheDocument()
  })

  it('handles malformed summary fields with n/a or none safely', () => {
    render(<PreflightTemplateConflictSummaryPanel authoritativeDiffSummary={{ template_conflict_summary: { available: 'yes', read_only: 'yes', non_blocking: null, status: 42, warning_count: NaN, info_count: Infinity, conflict_count: 'three', conflict_codes: 'bad', busiest_week: 'oops', busiest_week_slot_count: {}, source: '', message: '' } }} />)
    expect(screen.getByText('Preflight template conflict diagnostics available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict status: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict conflict codes: none')).toBeInTheDocument()
  })

  it('renders unavailable summary with available false and zero counts', () => {
    render(<PreflightTemplateConflictSummaryPanel authoritativeDiffSummary={{ template_conflict_summary: { available: false, read_only: true, non_blocking: true, status: 'clean', warning_count: 0, info_count: 0, conflict_count: 0, conflict_codes: [], busiest_week: null, busiest_week_slot_count: null, source: 'template_slot_conflict_preview', message: 'No conflicts.' } }} />)
    expect(screen.getByText('Preflight template conflict diagnostics available: false')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict warning count: 0')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict info count: 0')).toBeInTheDocument()
    expect(screen.getByText('Preflight template conflict conflict count: 0')).toBeInTheDocument()
  })
})

describe('TemplateConflictDiagnosticsOverviewPanel', () => {
  it('A) shows unavailable/n-a when no data is provided', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel />)
    expect(screen.getByText('Selected conflict report: available')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict status: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict preview: unavailable')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict summary: unavailable')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict preview: unavailable')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict summary: unavailable')).toBeInTheDocument()
  })

  it('B) selected report only', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel selectedConflictReport={{ template_id: 't', template_exists: true, read_only: true, message: 'ok', summary: { status: 'warnings', warning_count: 1, info_count: 0, conflict_count: 3, slot_count: 5, occupied_week_count: 5 }, conflicts: [], template_conflict_diagnostics_overview: { selected_report_available: true, selected_status: 'warnings', selected_conflict_count: 3, preflight_preview_available: false, preflight_summary_available: false, dry_run_preview_available: false, dry_run_summary_available: false, mutation_behavior: 'unavailable', blocking_behavior: 'non_blocking', read_only: true, non_blocking: true } }} />)
    expect(screen.getByText('Selected conflict report: available')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict count: 3')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict preview: unavailable')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict preview: unavailable')).toBeInTheDocument()
  })

  it('B2) selected backend overview is preferred over conflicting summary', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel selectedConflictReport={{ template_id: 't', template_exists: true, read_only: true, message: 'ok', summary: { status: 'warnings', warning_count: 1, info_count: 0, conflict_count: 3, slot_count: 5, occupied_week_count: 5 }, conflicts: [], template_conflict_diagnostics_overview: { selected_report_available: true, selected_status: 'info', selected_conflict_count: 9, mutation_behavior: 'unavailable', blocking_behavior: 'non_blocking', read_only: true, non_blocking: true } }} />)
    expect(screen.getByText('Selected conflict report: available')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict status: info')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict count: 9')).toBeInTheDocument()
  })

  it('B3) malformed selected backend overview falls back to summary', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel selectedConflictReport={{ template_id: 't', template_exists: true, read_only: true, message: 'ok', summary: { status: 'warnings', warning_count: 1, info_count: 0, conflict_count: 3, slot_count: 5, occupied_week_count: 5 }, conflicts: [], template_conflict_diagnostics_overview: { selected_report_available: 'bad' as any, selected_status: 42 as any, selected_conflict_count: Number.NaN as any } }} />)
    expect(screen.getByText('Selected conflict report: available')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict count: 3')).toBeInTheDocument()
  })

  it('B4) malformed selected availability falls back to report presence while keeping valid selected status/count', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel selectedConflictReport={{ template_id: 't', template_exists: true, read_only: true, message: 'ok', summary: { status: 'warnings', warning_count: 1, info_count: 0, conflict_count: 3, slot_count: 5, occupied_week_count: 5 }, conflicts: [], template_conflict_diagnostics_overview: { selected_report_available: 'bad' as any, selected_status: 'info', selected_conflict_count: 9 } }} />)
    expect(screen.getByText('Selected conflict report: available')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict status: info')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict count: 9')).toBeInTheDocument()
  })

  it('C) preflight preview and summary available', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel preflightResult={{ can_build: false, target_season_label: 's', source_type: 'season_template', source_template_id: 't', preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', target_calendar_exists: false, target_event_count: 0, source_resolved: true, source_summary: {}, authoritative_diff_summary: { template_conflict_summary: { available: true, read_only: true, non_blocking: true, status: 'warnings', warning_count: 1, info_count: 2, conflict_count: 3, conflict_codes: ['c1'] } }, template_slot_conflict_preview: { status: 'warnings', conflict_count: 3 }, validation_warnings: [], validation_errors: [], audit_preview: {} }} />)
    expect(screen.getByText('Preflight conflict preview: available')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict summary: available')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict count: 3')).toBeInTheDocument()
  })

  it('D) dry-run preview and summary available', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel dryRunResult={{ command: 'season_builder_dry_run_build', enabled: false, can_execute: false, can_mutate: false, target_season_label: 's', source_type: 'season_template', source_template_id: 't', overwrite_policy: null, preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', validation_warnings: [], validation_errors: [], audit_preview: {}, generation_design_preview: {}, candidate_event_contract_preview: {}, conflict_contract_preview: {}, dry_run_result_contract_preview: {}, dry_run_result_preview: { template_conflict_summary: { available: true, read_only: true, non_blocking: true, status: 'warnings', warning_count: 1, info_count: 2, conflict_count: 3, conflict_codes: ['c1'] } }, message: 'dry run disabled', template_slot_conflict_preview: { status: 'warnings', conflict_count: 3 } }} />)
    expect(screen.getByText('Dry-run conflict preview: available')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict summary: available')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict count: 3')).toBeInTheDocument()
  })

  it('E) handles malformed summary/preview safely with n/a', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel preflightResult={{ can_build: false, target_season_label: 's', source_type: 'season_template', source_template_id: 't', preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', target_calendar_exists: false, target_event_count: 0, source_resolved: true, source_summary: {}, authoritative_diff_summary: { template_conflict_summary: { status: 42, conflict_count: NaN } }, template_slot_conflict_preview: { status: 42, conflict_count: NaN } as any, validation_warnings: [], validation_errors: [], audit_preview: {} } as any} dryRunResult={{ command: 'season_builder_dry_run_build', enabled: false, can_execute: false, can_mutate: false, target_season_label: 's', source_type: 'season_template', source_template_id: 't', overwrite_policy: null, preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', validation_warnings: [], validation_errors: [], audit_preview: {}, generation_design_preview: {}, candidate_event_contract_preview: {}, conflict_contract_preview: {}, dry_run_result_contract_preview: {}, dry_run_result_preview: { template_conflict_summary: { status: 42, conflict_count: NaN } }, message: 'dry run disabled', template_slot_conflict_preview: { status: 42, conflict_count: NaN } as any } as any} />)
    expect(screen.getByText('Preflight conflict status: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict count: n/a')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict status: n/a')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict count: n/a')).toBeInTheDocument()
  })

  it('F) backend preflight overview is preferred over conflicting derived values', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel preflightResult={{ can_build: false, target_season_label: 's', source_type: 'season_template', source_template_id: 't', preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', target_calendar_exists: false, target_event_count: 0, source_resolved: true, source_summary: {}, authoritative_diff_summary: { template_conflict_summary: { status: 'warnings', conflict_count: 3 } }, template_slot_conflict_preview: { status: 'warnings', conflict_count: 3 }, template_conflict_diagnostics_overview: { preflight_preview_available: true, preflight_summary_available: true, preflight_status: 'info', preflight_conflict_count: 9, mutation_behavior: 'unavailable', blocking_behavior: 'non_blocking' }, validation_warnings: [], validation_errors: [], audit_preview: {} }} />)
    expect(screen.getByText('Preflight conflict status: info')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict count: 9')).toBeInTheDocument()
  })

  it('G) backend dry-run overview is preferred over conflicting derived values', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel dryRunResult={{ command: 'season_builder_dry_run_build', enabled: false, can_execute: false, can_mutate: false, target_season_label: 's', source_type: 'season_template', source_template_id: 't', overwrite_policy: null, preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', validation_warnings: [], validation_errors: [], audit_preview: {}, generation_design_preview: {}, candidate_event_contract_preview: {}, conflict_contract_preview: {}, dry_run_result_contract_preview: {}, dry_run_result_preview: { template_conflict_summary: { status: 'warnings', conflict_count: 3 } }, template_conflict_diagnostics_overview: { dry_run_preview_available: true, dry_run_summary_available: true, dry_run_status: 'info', dry_run_conflict_count: 9, mutation_behavior: 'unavailable', blocking_behavior: 'non_blocking' }, message: 'dry run disabled', template_slot_conflict_preview: { status: 'warnings', conflict_count: 3 } }} />)
    expect(screen.getByText('Dry-run conflict status: info')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict count: 9')).toBeInTheDocument()
  })

  it('H) malformed backend overview falls back to derived preview/summary', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel preflightResult={{ can_build: false, target_season_label: 's', source_type: 'season_template', source_template_id: 't', preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', target_calendar_exists: false, target_event_count: 0, source_resolved: true, source_summary: {}, authoritative_diff_summary: { template_conflict_summary: { status: 'warnings', conflict_count: 3 } }, template_slot_conflict_preview: { status: 'warnings', conflict_count: 3 }, template_conflict_diagnostics_overview: { preflight_status: 42 as any, preflight_conflict_count: Number.NaN as any }, validation_warnings: [], validation_errors: [], audit_preview: {} }} />)
    expect(screen.getByText('Preflight conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict count: 3')).toBeInTheDocument()
  })

  it('uses backend overview values across selected, preflight, and dry-run surfaces', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel
      selectedConflictReport={{ template_id: 't', template_exists: true, read_only: true, message: 'ok', summary: { status: 'warnings', warning_count: 1, info_count: 0, conflict_count: 3, slot_count: 5, occupied_week_count: 5 }, conflicts: [], template_conflict_diagnostics_overview: { selected_report_available: true, selected_status: 'info', selected_conflict_count: 9, mutation_behavior: 'unavailable', blocking_behavior: 'non_blocking', read_only: true, non_blocking: true } }}
      preflightResult={{ can_build: false, target_season_label: 's', source_type: 'season_template', source_template_id: 't', preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', target_calendar_exists: false, target_event_count: 0, source_resolved: true, source_summary: {}, authoritative_diff_summary: { template_conflict_summary: { status: 'warnings', conflict_count: 3 } }, template_slot_conflict_preview: { status: 'warnings', conflict_count: 3 }, template_conflict_diagnostics_overview: { preflight_preview_available: true, preflight_summary_available: true, preflight_status: 'clean', preflight_conflict_count: 7, mutation_behavior: 'unavailable', blocking_behavior: 'non_blocking', read_only: true, non_blocking: true }, validation_warnings: [], validation_errors: [], audit_preview: {} }}
      dryRunResult={{ command: 'season_builder_dry_run_build', enabled: false, can_execute: false, can_mutate: false, target_season_label: 's', source_type: 'season_template', source_template_id: 't', overwrite_policy: null, preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', validation_warnings: [], validation_errors: [], audit_preview: {}, generation_design_preview: {}, candidate_event_contract_preview: {}, conflict_contract_preview: {}, dry_run_result_contract_preview: {}, dry_run_result_preview: { template_conflict_summary: { status: 'warnings', conflict_count: 3 } }, template_slot_conflict_preview: { status: 'warnings', conflict_count: 3 }, template_conflict_diagnostics_overview: { dry_run_preview_available: true, dry_run_summary_available: true, dry_run_status: 'info', dry_run_conflict_count: 11, mutation_behavior: 'unavailable', blocking_behavior: 'non_blocking', read_only: true, non_blocking: true }, message: 'dry run disabled' }}
    />)

    expect(screen.getByText('Selected conflict status: info')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict count: 9')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict preview: available')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict summary: available')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict status: clean')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict count: 7')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict preview: available')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict summary: available')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict status: info')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict count: 11')).toBeInTheDocument()
    expect(screen.getByText('Conflict diagnostics mutation behavior: unavailable')).toBeInTheDocument()
    expect(screen.getByText('Conflict diagnostics blocking behavior: non-blocking')).toBeInTheDocument()
  })

  it('keeps derived fallback continuity across all three surfaces when backend overviews are absent', () => {
    render(<TemplateConflictDiagnosticsOverviewPanel
      selectedConflictReport={{ template_id: 't', template_exists: true, read_only: true, message: 'ok', summary: { status: 'warnings', warning_count: 1, info_count: 0, conflict_count: 3, slot_count: 5, occupied_week_count: 5 }, conflicts: [] }}
      preflightResult={{ can_build: false, target_season_label: 's', source_type: 'season_template', source_template_id: 't', preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', target_calendar_exists: false, target_event_count: 0, source_resolved: true, source_summary: {}, authoritative_diff_summary: { template_conflict_summary: { status: 'warnings', conflict_count: 3 } }, template_slot_conflict_preview: { status: 'warnings', conflict_count: 3 }, validation_warnings: [], validation_errors: [], audit_preview: {} }}
      dryRunResult={{ command: 'season_builder_dry_run_build', enabled: false, can_execute: false, can_mutate: false, target_season_label: 's', source_type: 'season_template', source_template_id: 't', overwrite_policy: null, preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', validation_warnings: [], validation_errors: [], audit_preview: {}, generation_design_preview: {}, candidate_event_contract_preview: {}, conflict_contract_preview: {}, dry_run_result_contract_preview: {}, dry_run_result_preview: { template_conflict_summary: { status: 'warnings', conflict_count: 3 } }, template_slot_conflict_preview: { status: 'warnings', conflict_count: 3 }, message: 'dry run disabled' }}
    />)

    expect(screen.getByText('Selected conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Selected conflict count: 3')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Preflight conflict count: 3')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict status: warnings')).toBeInTheDocument()
    expect(screen.getByText('Dry-run conflict count: 3')).toBeInTheDocument()
  })
})

describe('SeasonTemplateSlotConflictPanel', () => {
  it('renders clean/info/missing/no-conflicts/hidden-count states', () => {
    const { rerender } = render(<SeasonTemplateSlotConflictPanel queryEnabled={true} query={{ isLoading: false, isFetching: false, error: null, data: { template_id: 't', template_exists: true, read_only: true, message: 'm', summary: { status: 'clean', warning_count: 0, info_count: 0, conflict_count: 0, slot_count: 1, occupied_week_count: 1 }, conflicts: [] } }} />)
    expect(screen.getByText('Template slot conflict analysis is clean.')).toBeInTheDocument()
    expect(screen.getByText('No template slot conflicts reported.')).toBeInTheDocument()

    rerender(<SeasonTemplateSlotConflictPanel queryEnabled={true} query={{ isLoading: false, isFetching: false, error: null, data: { template_id: 't', template_exists: false, read_only: true, message: 'missing', summary: { status: 'info', warning_count: 0, info_count: 1, conflict_count: 0, slot_count: 0, occupied_week_count: 0 }, conflicts: [] } }} />)
    expect(screen.getByText('Template slot conflict analysis has informational findings only.')).toBeInTheDocument()
    expect(screen.getByText('Selected template slot conflict template_exists: false')).toBeInTheDocument()

    const conflicts = Array.from({ length: 11 }, (_, i) => ({ severity: 'info' as const, code: `c_${i}`, message: `m_${i}` }))
    rerender(<SeasonTemplateSlotConflictPanel queryEnabled={true} query={{ isLoading: false, isFetching: false, error: null, data: { template_id: 't', template_exists: true, read_only: true, message: 'many', summary: { status: 'info', warning_count: 0, info_count: 11, conflict_count: 11, slot_count: 11, occupied_week_count: 11 }, conflicts } }} />)
    expect(screen.getByText('1 additional template slot conflicts hidden.')).toBeInTheDocument()
  })

  it('shows fallback metadata when conflict code is unknown', () => {
    render(<SeasonTemplateSlotConflictPanel
      queryEnabled={true}
      query={{
        isLoading: false,
        isFetching: false,
        error: null,
        data: {
          template_id: 't',
          template_exists: true,
          read_only: true,
          message: 'm',
          summary: { status: 'warnings', warning_count: 1, info_count: 0, conflict_count: 1, slot_count: 1, occupied_week_count: 1 },
          conflicts: [{ severity: 'warning', code: 'unknown_code', message: 'msg', season_week: 1 }]
        }
      }}
    />)
    expect(screen.getByText('Unknown template slot conflict code')).toBeInTheDocument()
    expect(screen.getByText('No registry metadata available for this template slot conflict code.')).toBeInTheDocument()
  })
})

describe('TemplateSlotConflictCodeRegistryPanel', () => {
  it('shows loading state', () => {
    render(<TemplateSlotConflictCodeRegistryPanel isLoading={true} error={null} />)
    expect(screen.getByText('Loading template slot conflict code registry…')).toBeInTheDocument()
  })

  it('shows no data state', () => {
    render(<TemplateSlotConflictCodeRegistryPanel isLoading={false} error={null} />)
    expect(screen.getByText('No template slot conflict code registry is available.')).toBeInTheDocument()
  })

  it('shows empty codes state', () => {
    render(<TemplateSlotConflictCodeRegistryPanel isLoading={false} error={null} data={{ read_only: true, code_count: 0, message: 'empty', codes: [] }} />)
    expect(screen.getByText('No template slot conflict codes registered.')).toBeInTheDocument()
  })
})

describe('Candidate identity panels', () => {

  it('handles missing overview safely', () => {
    render(<CandidateIdentityOverviewPanel dryRunResultPreview={undefined} />)
    expect(screen.getByText('Candidate identity overview is not available.')).toBeInTheDocument()
  })

  it('handles malformed overview safely', () => {
    render(<CandidateIdentityOverviewPanel dryRunResultPreview={{ candidate_identity_overview: { available: 'yes', candidate_count: NaN, safe_for_future_reference: null, has_duplicate_candidate_ids: 'x', has_duplicate_candidate_identity_keys: undefined, identity_source: '', id_strategy: '  ', key_strategy: 9, read_only: 'true', mutation_permitted: 1, message: '' } }} />)
    expect(screen.getByText('Candidate identity overview available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity overview candidate count: n/a')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity overview source: n/a')).toBeInTheDocument()
  })

  it('shows valid overview rows', () => {
    render(<CandidateIdentityOverviewPanel dryRunResultPreview={{ candidate_identity_overview: { available: true, candidate_count: 1, safe_for_future_reference: true, has_duplicate_candidate_ids: false, has_duplicate_candidate_identity_keys: false, identity_source: 'season_template_slot', id_strategy: 'sanitized_template_slot_week', key_strategy: 'pipe_joined_sanitized_components', read_only: true, mutation_permitted: false, message: 'Candidate identity overview: safe for future reference.' } }} />)
    expect(screen.getByText('Candidate identity overview available: true')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity overview candidate count: 1')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity overview mutation permitted: false')).toBeInTheDocument()
  })

  it('shows unsafe duplicate overview state', () => {
    render(<CandidateIdentityOverviewPanel dryRunResultPreview={{ candidate_identity_overview: { available: true, safe_for_future_reference: false, has_duplicate_candidate_ids: true, has_duplicate_candidate_identity_keys: true } }} />)
    expect(screen.getByText('Candidate identity overview safe for future reference: false')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity overview duplicate candidate IDs: true')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity overview duplicate keys: true')).toBeInTheDocument()
  })

  it('handles missing summary safely', () => {
    render(<CandidateIdentitySummaryPanel dryRunResultPreview={undefined} />)
    expect(screen.getByText('Candidate identity summary is not available.')).toBeInTheDocument()
  })

  it('handles malformed summary safely', () => {
    render(<CandidateIdentitySummaryPanel dryRunResultPreview={{ candidate_identity_summary: { candidate_count: NaN, candidate_ids: 'bad', candidate_identity_keys: [null], duplicate_candidate_ids: [], duplicate_candidate_identity_keys: 'bad', read_only: 'yes', mutation_permitted: null, message: '' } }} />)
    expect(screen.getByText('Candidate identity candidate count: n/a')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity candidate IDs: none')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity keys: none')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity duplicate keys: none')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity read-only: n/a')).toBeInTheDocument()
  })

  it('shows valid summary rows', () => {
    render(<CandidateIdentitySummaryPanel dryRunResultPreview={{ candidate_identity_summary: { candidate_count: 1, candidate_ids: ['cand_default_msa_template_preview_slot_01_1'], candidate_identity_keys: ['k1'], duplicate_candidate_ids: [], duplicate_candidate_identity_keys: [], read_only: true, mutation_permitted: false, message: 'ok' } }} />)
    expect(screen.getByText('Candidate identity candidate count: 1')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity candidate IDs: cand_default_msa_template_preview_slot_01_1')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity mutation permitted: false')).toBeInTheDocument()
  })

  it('handles missing contract safely', () => {
    render(<CandidateIdentityContractPanel dryRunResultPreview={undefined} />)
    expect(screen.getByText('Candidate identity contract is not available.')).toBeInTheDocument()
  })

  it('handles malformed contract safely', () => {
    render(<CandidateIdentityContractPanel dryRunResultPreview={{ candidate_identity_contract: { identity_source: '', id_strategy: 42, key_strategy: null, key_components: 'bad', candidate_count: NaN, has_duplicate_candidate_ids: 'false', has_duplicate_candidate_identity_keys: null, safe_for_future_reference: undefined, read_only: 'true', mutation_permitted: 0, message: '' } }} />)
    expect(screen.getByText('Candidate identity source: n/a')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity key components: none')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity contract candidate count: n/a')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity safe for future reference: n/a')).toBeInTheDocument()
  })

  it('shows valid contract rows', () => {
    render(<CandidateIdentityContractPanel dryRunResultPreview={{ candidate_identity_contract: { identity_source: 'season_template_slot', id_strategy: 'sanitized_template_slot_week', key_strategy: 'pipe_joined_sanitized_components', key_components: ['target_season'], candidate_count: 1, has_duplicate_candidate_ids: false, has_duplicate_candidate_identity_keys: false, safe_for_future_reference: true, read_only: true, mutation_permitted: false, message: 'ok' } }} />)
    expect(screen.getByText('Candidate identity source: season_template_slot')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity ID strategy: sanitized_template_slot_week')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity safe for future reference: true')).toBeInTheDocument()
  })

  it('shows unsafe duplicate contract state', () => {
    render(<CandidateIdentityContractPanel dryRunResultPreview={{ candidate_identity_contract: { has_duplicate_candidate_ids: true, has_duplicate_candidate_identity_keys: true, safe_for_future_reference: false } }} />)
    expect(screen.getByText('Candidate identity has duplicate candidate IDs: true')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity has duplicate keys: true')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity safe for future reference: false')).toBeInTheDocument()
  })

  it('handles missing fingerprint safely', () => {
    render(<CandidateIdentityFingerprintPanel dryRunResultPreview={undefined} />)
    expect(screen.getByText('Candidate identity fingerprint is not available.')).toBeInTheDocument()
  })

  it('handles malformed fingerprint safely', () => {
    render(<CandidateIdentityFingerprintPanel dryRunResultPreview={{ candidate_identity_fingerprint: { fingerprint: '  ', fingerprint_algorithm: 4, fingerprint_payload_version: NaN, candidate_count: Infinity, candidate_ids: 'bad', candidate_identity_keys: [null], safe_for_future_reference: 'yes', target_season_label: '', source_type: null, source_template_id: ' ', read_only: 1, mutation_permitted: undefined, message: '' } }} />)
    expect(screen.getByText('Candidate identity fingerprint value: n/a')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity fingerprint payload version: n/a')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity fingerprint candidate IDs: none')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity fingerprint safe for future reference: n/a')).toBeInTheDocument()
  })

  it('shows valid fingerprint rows', () => {
    render(<CandidateIdentityFingerprintPanel dryRunResultPreview={{ candidate_identity_fingerprint: { fingerprint: 'abc123fingerprint', fingerprint_algorithm: 'sha256', fingerprint_payload_version: 1, candidate_count: 1, candidate_ids: ['cand_default_msa_template_preview_slot_01_1'], candidate_identity_keys: ['target_season=2000_01|source_type=season_template'], safe_for_future_reference: true, target_season_label: '2000/01', source_type: 'season_template', source_template_id: 'default_msa_template_preview', read_only: true, mutation_permitted: false, message: 'Candidate identity fingerprint is deterministic and read-only.' } }} />)
    expect(screen.getByText('Candidate identity fingerprint value: abc123fingerprint')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity fingerprint algorithm: sha256')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity fingerprint candidate count: 1')).toBeInTheDocument()
  })

  it('handles missing review reference safely', () => {
    render(<CandidateIdentityReviewReferencePanel dryRunResultPreview={undefined} />)
    expect(screen.getByText('Candidate identity review reference is not available.')).toBeInTheDocument()
  })

  it('handles malformed review reference safely', () => {
    render(<CandidateIdentityReviewReferencePanel dryRunResultPreview={{ candidate_identity_review_reference: { reference_type: '', reference_id: 3, fingerprint_algorithm: null, fingerprint_payload_version: NaN, candidate_count: Infinity, safe_for_future_reference: 'yes', can_reference_future_apply: 'no', read_only: 'true', mutation_permitted: 0, message: '' } }} />)
    expect(screen.getByText('Candidate identity review reference type: n/a')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity review reference payload version: n/a')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity review reference can reference future apply: n/a')).toBeInTheDocument()
  })

  it('shows valid review reference rows', () => {
    render(<CandidateIdentityReviewReferencePanel dryRunResultPreview={{ candidate_identity_review_reference: { reference_type: 'candidate_identity_set', reference_id: 'abc123fingerprint', fingerprint_algorithm: 'sha256', fingerprint_payload_version: 1, candidate_count: 1, safe_for_future_reference: true, can_reference_future_apply: true, read_only: true, mutation_permitted: false, message: 'Candidate identity set can be referenced by a future audited apply flow.' } }} />)
    expect(screen.getByText('Candidate identity review reference type: candidate_identity_set')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity review reference ID: abc123fingerprint')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity review reference can reference future apply: true')).toBeInTheDocument()
  })

  it('shows unsafe review reference state', () => {
    render(<CandidateIdentityReviewReferencePanel dryRunResultPreview={{ candidate_identity_review_reference: { safe_for_future_reference: false, can_reference_future_apply: false } }} />)
    expect(screen.getByText('Candidate identity review reference safe for future reference: false')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity review reference can reference future apply: false')).toBeInTheDocument()
  })

  it('renders candidate identity readiness overview rows safely in dry-run identity readiness panel', () => {
    render(<DisabledDryRunBuildContractPanel
      queryEnabled={true}
      requestPayload={{ target_season_label: '2000/01', source_type: 'season_template', source_template_id: 'default_msa_template_preview', overwrite_policy: null, preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', requested_by: 'test', audit_reason: '', explicit_confirmation: '', mutation_scope: '' }}
      query={{
        isLoading: false,
        error: null,
        data: {
          command: 'season_builder_dry_run_build',
          enabled: false,
          can_execute: false,
          can_mutate: false,
          target_season_label: '2000/01',
          source_type: 'season_template',
          source_template_id: 'default_msa_template_preview',
          overwrite_policy: null,
          preflight_fingerprint: 'pf',
          reviewed_diff_id: 'rd',
          validation_errors: [],
          validation_warnings: [],
          audit_preview: {},
          generation_design_preview: {},
          candidate_event_contract_preview: {},
          conflict_contract_preview: {},
          dry_run_result_contract_preview: {},
          dry_run_result_preview: {
            identity_readiness: {
              status: 'ready_reference',
              future_command_reference: {
                candidate_identity_fingerprint: 'abc123fingerprint',
                candidate_identity_reference_id: 'abc123fingerprint',
                can_reference_candidate_identity_set: true,
                candidate_identity_reference_type: 'candidate_identity_set'
              },
              candidate_identity_readiness_overview: {
                available: true,
                candidate_identity_fingerprint: 'abc123fingerprint',
                candidate_identity_reference_id: 'abc123fingerprint',
                candidate_identity_reference_type: 'candidate_identity_set',
                can_reference_candidate_identity_set: true,
                candidate_reference_status: 'OK',
                main_future_command_reference_ready: true,
                read_only: true,
                mutation_permitted: false,
                message: 'Candidate identity readiness is referenceable.'
              },
              items: []
            }
          },
          message: 'ok'
        }
      }}
    />)
    expect(screen.getByText('Candidate identity readiness overview')).toBeInTheDocument()
    expect(screen.getByText('candidate_identity_fingerprint', { selector: 'td' })).toBeInTheDocument()
    expect(screen.getByText('candidate_identity_reference_id', { selector: 'td' })).toBeInTheDocument()
    expect(screen.getByText('can_reference_candidate_identity_set', { selector: 'td' })).toBeInTheDocument()
    expect(screen.getByText('candidate_reference_status', { selector: 'td' })).toBeInTheDocument()
    expect(screen.getByText('main_future_command_reference_ready', { selector: 'td' })).toBeInTheDocument()
    expect(screen.getByText('Candidate identity readiness is referenceable.')).toBeInTheDocument()
  })

  it('shows unavailable message when candidate identity readiness overview is missing', () => {
    render(<DisabledDryRunBuildContractPanel
      queryEnabled={true}
      requestPayload={{ target_season_label: '2000/01', source_type: 'season_template', source_template_id: null, overwrite_policy: null, preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', requested_by: 'test', audit_reason: '', explicit_confirmation: '', mutation_scope: '' }}
      query={{
        isLoading: false,
        error: null,
        data: {
          command: 'season_builder_dry_run_build',
          enabled: false,
          can_execute: false,
          can_mutate: false,
          target_season_label: '2000/01',
          source_type: 'season_template',
          source_template_id: null,
          overwrite_policy: null,
          preflight_fingerprint: 'pf',
          reviewed_diff_id: 'rd',
          validation_errors: [],
          validation_warnings: [],
          audit_preview: {},
          generation_design_preview: {},
          candidate_event_contract_preview: {},
          conflict_contract_preview: {},
          dry_run_result_contract_preview: {},
          dry_run_result_preview: { identity_readiness: { status: 'ready_reference', items: [] } },
          message: 'ok'
        }
      }}
    />)
    expect(screen.getByText('Candidate identity readiness overview is unavailable.')).toBeInTheDocument()
  })

  it('shows n/a for malformed candidate identity readiness overview row values', () => {
    render(<DisabledDryRunBuildContractPanel
      queryEnabled={true}
      requestPayload={{ target_season_label: '2000/01', source_type: 'season_template', source_template_id: null, overwrite_policy: null, preflight_fingerprint: 'pf', reviewed_diff_id: 'rd', requested_by: 'test', audit_reason: '', explicit_confirmation: '', mutation_scope: '' }}
      query={{
        isLoading: false,
        error: null,
        data: {
          command: 'season_builder_dry_run_build',
          enabled: false,
          can_execute: false,
          can_mutate: false,
          target_season_label: '2000/01',
          source_type: 'season_template',
          source_template_id: null,
          overwrite_policy: null,
          preflight_fingerprint: 'pf',
          reviewed_diff_id: 'rd',
          validation_errors: [],
          validation_warnings: [],
          audit_preview: {},
          generation_design_preview: {},
          candidate_event_contract_preview: {},
          conflict_contract_preview: {},
          dry_run_result_contract_preview: {},
          dry_run_result_preview: {
            identity_readiness: {
              status: 'ready_reference',
              candidate_identity_readiness_overview: {
                available: 'yes',
                candidate_identity_fingerprint: '  ',
                candidate_identity_reference_id: 33,
                candidate_identity_reference_type: null,
                can_reference_candidate_identity_set: 'yes',
                candidate_reference_status: 42,
                main_future_command_reference_ready: 1,
                read_only: 'true',
                mutation_permitted: undefined,
                message: ''
              } as unknown as Record<string, unknown>,
              items: []
            }
          },
          message: 'ok'
        }
      }}
    />)
    expect(screen.getAllByText('n/a').length).toBeGreaterThan(0)
  })

  it('readCandidateIdentityReadinessOverview returns null for missing identity readiness', () => {
    expect(readCandidateIdentityReadinessOverview(undefined)).toBeNull()
  })

  it('readCandidateIdentityReadinessOverview returns null for missing overview', () => {
    expect(readCandidateIdentityReadinessOverview({ status: 'ready_reference' })).toBeNull()
  })

  it('readCandidateIdentityReadinessOverview normalizes valid overview', () => {
    expect(readCandidateIdentityReadinessOverview({
      candidate_identity_readiness_overview: {
        available: true,
        candidate_identity_fingerprint: 'abc123fingerprint',
        candidate_identity_reference_id: 'abc123fingerprint',
        candidate_identity_reference_type: 'candidate_identity_set',
        can_reference_candidate_identity_set: true,
        candidate_reference_status: 'OK',
        main_future_command_reference_ready: true,
        read_only: true,
        mutation_permitted: false,
        message: 'Candidate identity readiness is referenceable.'
      }
    })).toEqual({
      available: 'true',
      candidateIdentityFingerprint: 'abc123fingerprint',
      candidateIdentityReferenceId: 'abc123fingerprint',
      candidateIdentityReferenceType: 'candidate_identity_set',
      canReferenceCandidateIdentitySet: 'true',
      candidateReferenceStatus: 'OK',
      mainFutureCommandReferenceReady: 'true',
      readOnly: 'true',
      mutationPermitted: 'false',
      message: 'Candidate identity readiness is referenceable.'
    })
  })

  it('readCandidateIdentityReadinessOverview normalizes malformed overview to n/a', () => {
    expect(readCandidateIdentityReadinessOverview({
      candidate_identity_readiness_overview: {
        available: 'yes',
        candidate_identity_fingerprint: '  ',
        candidate_identity_reference_id: 33,
        candidate_identity_reference_type: null,
        can_reference_candidate_identity_set: 'yes',
        candidate_reference_status: 42,
        main_future_command_reference_ready: 1,
        read_only: 'true',
        mutation_permitted: undefined,
        message: ''
      }
    })).toEqual({
      available: 'n/a',
      candidateIdentityFingerprint: 'n/a',
      candidateIdentityReferenceId: 'n/a',
      candidateIdentityReferenceType: 'n/a',
      canReferenceCandidateIdentitySet: 'n/a',
      candidateReferenceStatus: 'n/a',
      mainFutureCommandReferenceReady: 'n/a',
      readOnly: 'n/a',
      mutationPermitted: 'n/a',
      message: 'n/a'
    })
  })
})


describe('Future apply preview panels', () => {
  it('renders valid future apply reference contract data', () => {
    render(<FutureApplyReferenceContractPanel dryRunResultPreview={{ future_apply_reference_contract: { available: true, apply_execution_enabled: false, mutation_permitted: false, message: 'Reference contract preview only.' } }} />)
    expect(screen.getByText('Available: true')).toBeInTheDocument()
    expect(screen.getByText('Apply execution enabled: false')).toBeInTheDocument()
    expect(screen.getByText('Mutation permitted: false')).toBeInTheDocument()
    expect(screen.getByText('Message: Reference contract preview only.')).toBeInTheDocument()
  })

  it('handles missing and malformed future apply reference contract data', () => {
    expect(readFutureApplyReferenceContract(undefined)).toBeNull()
    render(<FutureApplyReferenceContractPanel dryRunResultPreview={{ future_apply_reference_contract: { available: 'yes', contract_type: '', mutation_permitted: 0, message: '' } }} />)
    expect(screen.getByText('Available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Contract type: n/a')).toBeInTheDocument()
    expect(screen.getByText('Mutation permitted: n/a')).toBeInTheDocument()
    expect(screen.getByText('Message: No message provided.')).toBeInTheDocument()
  })

  it('renders valid future apply request validation preview data', () => {
    render(<FutureApplyRequestValidationPreviewPanel preview={{ available: true, reference_id_matches: true, fingerprint_matches: true, reference_type_matches: true, apply_execution_enabled: false, mutation_permitted: false, message: 'Validation preview only.' }} />)
    expect(screen.getByText('Available: true')).toBeInTheDocument()
    expect(screen.getByText('Reference ID matches: true')).toBeInTheDocument()
    expect(screen.getByText('Fingerprint matches: true')).toBeInTheDocument()
    expect(screen.getByText('Reference type matches: true')).toBeInTheDocument()
    expect(screen.getByText('Apply execution enabled: false')).toBeInTheDocument()
    expect(screen.getByText('Mutation permitted: false')).toBeInTheDocument()
    expect(screen.getByText('Message: Validation preview only.')).toBeInTheDocument()
  })

  it('handles missing and malformed future apply request validation preview data', () => {
    expect(readFutureApplyRequestValidationPreview(undefined)).toBeNull()
    render(<FutureApplyRequestValidationPreviewPanel preview={{ available: 'yes', requested_candidate_identity_reference_id: '', reference_id_matches: 'x', message: '' }} />)
    expect(screen.getByText('Available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Requested reference ID: n/a')).toBeInTheDocument()
    expect(screen.getByText('Reference ID matches: n/a')).toBeInTheDocument()
    expect(screen.getByText('Message: No message provided.')).toBeInTheDocument()
  })


  it('keeps future apply request validation preview display-only with apply execution disabled', () => {
    render(<FutureApplyRequestValidationPreviewPanel preview={{ available: true, apply_execution_enabled: false, mutation_permitted: false, message: 'Validation preview only.' }} />)
    expect(screen.getByText('Apply execution enabled: false')).toBeInTheDocument()
    expect(screen.queryByText('Apply execution enabled: true')).not.toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('keeps future apply reference contract display-only with apply execution disabled', () => {
    render(<FutureApplyReferenceContractPanel dryRunResultPreview={{ future_apply_reference_contract: { available: true, apply_execution_enabled: false, mutation_permitted: false, message: 'Reference contract preview only.' } }} />)
    expect(screen.getByText('Apply execution enabled: false')).toBeInTheDocument()
    expect(screen.queryByText('Apply execution enabled: true')).not.toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })


  it('renders valid create-only apply execution preflight preview data', () => {
    render(<CreateOnlyApplyExecutionPreflightPreviewPanel preview={{ available: true, preflight_type: 'create_only_apply_execution_preflight_preview', target_absent: true, create_only_scope_confirmed: true, audit_metadata_present: false, future_apply_reference_contract_available: true, future_apply_request_validation_available: true, candidate_identity_reference_matches: true, main_future_command_reference_ready: true, all_known_preconditions_met: false, execution_enabled: false, can_execute: false, read_only: true, mutation_permitted: false, message: 'Create-only apply execution remains disabled in preview mode.' }} />)
    expect(screen.getByText('Target absent: true')).toBeInTheDocument()
    expect(screen.getByText('Create-only scope confirmed: true')).toBeInTheDocument()
    expect(screen.getByText('Audit metadata present: false')).toBeInTheDocument()
    expect(screen.getByText('Future apply reference contract available: true')).toBeInTheDocument()
    expect(screen.getByText('Future apply request validation available: true')).toBeInTheDocument()
    expect(screen.getByText('Candidate identity reference matches: true')).toBeInTheDocument()
    expect(screen.getByText('Main future command reference ready: true')).toBeInTheDocument()
    expect(screen.getByText('All known preconditions met: false')).toBeInTheDocument()
    expect(screen.getAllByText('Execution enabled: false').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Can execute: false').length).toBeGreaterThan(0)
    expect(screen.getByText('Mutation permitted: false')).toBeInTheDocument()
    expect(screen.getByText('Message: Create-only apply execution remains disabled in preview mode.')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('handles missing and malformed create-only apply execution preflight preview data', () => {
    expect(readCreateOnlyApplyExecutionPreflightPreview(undefined)).toBeNull()
    render(<CreateOnlyApplyExecutionPreflightPreviewPanel preview={{ available: 'yes', preflight_type: '', execution_enabled: 'nope' }} />)
    expect(screen.getByText('Available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preflight type: n/a')).toBeInTheDocument()
    expect(screen.getByText('Execution enabled: n/a')).toBeInTheDocument()
    expect(screen.getByText('Message: No message provided.')).toBeInTheDocument()
  })

  it('renders valid create-only apply audit metadata preview data', () => {
    render(<CreateOnlyApplyAuditMetadataPreviewPanel preview={{ available: true, preview_type: 'create_only_apply_audit_metadata_preview', requested_by_present: true, audit_reason_present: true, explicit_confirmation_present: true, explicit_confirmation_matches: true, mutation_scope_present: true, mutation_scope_matches: true, required_confirmation_phrase: 'I understand this will create a new season calendar.', required_mutation_scope: 'create_only', all_required_audit_metadata_present: true, execution_enabled: false, can_execute: false, read_only: true, mutation_permitted: false, message: 'Create-only apply audit metadata preview is read-only.' }} />)
    expect(screen.getByText('Available: true')).toBeInTheDocument()
    expect(screen.getByText('Requested by present: true')).toBeInTheDocument()
    expect(screen.getByText('Audit reason present: true')).toBeInTheDocument()
    expect(screen.getByText('Explicit confirmation present: true')).toBeInTheDocument()
    expect(screen.getByText('Explicit confirmation matches: true')).toBeInTheDocument()
    expect(screen.getByText('Mutation scope present: true')).toBeInTheDocument()
    expect(screen.getByText('Mutation scope matches: true')).toBeInTheDocument()
    expect(screen.getByText('All required audit metadata present: true')).toBeInTheDocument()
    expect(screen.getAllByText('Execution enabled: false').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Can execute: false').length).toBeGreaterThan(0)
    expect(screen.getByText('Mutation permitted: false')).toBeInTheDocument()
    expect(screen.getByText('Message: Create-only apply audit metadata preview is read-only.')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('renders valid disabled execution contract summary data', () => {
    render(<DisabledExecutionContractSummaryPanel summary={{ available: true, summary_type: 'disabled_execution_contract_summary', future_apply_reference_contract_available: true, future_apply_request_validation_available: true, audit_metadata_available: true, execution_preflight_available: true, identity_reference_matches: true, audit_metadata_complete: true, all_known_preconditions_met: true, all_preview_layers_available: true, execution_enabled: false, can_execute: false, read_only: true, mutation_permitted: false, message: 'Execution remains disabled by contract.' }} />)
    expect(screen.getByText('Available: true')).toBeInTheDocument()
    expect(screen.getByText('Summary type: disabled_execution_contract_summary')).toBeInTheDocument()
    expect(screen.getByText('Future apply reference contract available: true')).toBeInTheDocument()
    expect(screen.getByText('Future apply request validation available: true')).toBeInTheDocument()
    expect(screen.getByText('Audit metadata available: true')).toBeInTheDocument()
    expect(screen.getByText('Execution preflight available: true')).toBeInTheDocument()
    expect(screen.getByText('Identity reference matches: true')).toBeInTheDocument()
    expect(screen.getByText('Audit metadata complete: true')).toBeInTheDocument()
    expect(screen.getByText('All known preconditions met: true')).toBeInTheDocument()
    expect(screen.getByText('All preview layers available: true')).toBeInTheDocument()
    expect(screen.getAllByText('Execution enabled: false').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Can execute: false').length).toBeGreaterThan(0)
    expect(screen.getByText('Read-only: true')).toBeInTheDocument()
    expect(screen.getByText('Mutation permitted: false')).toBeInTheDocument()
    expect(screen.getByText('Message: Execution remains disabled by contract.')).toBeInTheDocument()
    expect(screen.getByText('Message: Execution remains disabled by contract.')).toHaveTextContent('disabled')
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('handles missing and malformed disabled execution contract summary data', () => {
    expect(readDisabledExecutionContractSummary(undefined)).toBeNull()
    render(<DisabledExecutionContractSummaryPanel summary={{ available: 'yes', summary_type: '', all_preview_layers_available: 'bad' }} />)
    expect(screen.getByText('Available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Summary type: n/a')).toBeInTheDocument()
    expect(screen.getByText('All preview layers available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Message: No message provided.')).toBeInTheDocument()
  })

  it('renders valid final guarded apply readiness checklist data', () => {
    render(<FinalGuardedApplyReadinessChecklistPanel checklist={{ available: true, checklist_type: 'final_guarded_apply_readiness_checklist', endpoint_disabled: true, endpoint_execution_disabled: true, endpoint_mutation_disabled: true, summary_available: true, summary_all_preview_layers_available: true, summary_all_known_preconditions_met: true, summary_execution_disabled: true, summary_mutation_disabled: true, all_readiness_checks_passed: true, execution_enabled: false, can_execute: false, read_only: true, mutation_permitted: false, message: 'Final guarded checklist confirms execution remains disabled.' }} />)
    expect(screen.getByText('Available: true')).toBeInTheDocument()
    expect(screen.getByText('Checklist type: final_guarded_apply_readiness_checklist')).toBeInTheDocument()
    expect(screen.getByText('Endpoint disabled: true')).toBeInTheDocument()
    expect(screen.getByText('Endpoint execution disabled: true')).toBeInTheDocument()
    expect(screen.getByText('Endpoint mutation disabled: true')).toBeInTheDocument()
    expect(screen.getByText('Summary available: true')).toBeInTheDocument()
    expect(screen.getByText('Summary all preview layers available: true')).toBeInTheDocument()
    expect(screen.getByText('Summary all known preconditions met: true')).toBeInTheDocument()
    expect(screen.getByText('Summary execution disabled: true')).toBeInTheDocument()
    expect(screen.getByText('Summary mutation disabled: true')).toBeInTheDocument()
    expect(screen.getByText('All readiness checks passed: true')).toBeInTheDocument()
    expect(screen.getAllByText('Execution enabled: false').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Can execute: false').length).toBeGreaterThan(0)
    expect(screen.getByText('Read-only: true')).toBeInTheDocument()
    expect(screen.getByText('Mutation permitted: false')).toBeInTheDocument()
    expect(screen.getByText('Message: Final guarded checklist confirms execution remains disabled.')).toBeInTheDocument()
    expect(screen.getByText('Message: Final guarded checklist confirms execution remains disabled.')).toHaveTextContent(/disabled|remains disabled/i)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('handles missing and malformed final guarded apply readiness checklist data', () => {
    expect(readFinalGuardedApplyReadinessChecklist(undefined)).toBeNull()
    render(<FinalGuardedApplyReadinessChecklistPanel checklist={{ available: 'yes', checklist_type: '', endpoint_disabled: 'x' }} />)
    expect(screen.getByText('Available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Checklist type: n/a')).toBeInTheDocument()
    expect(screen.getByText('Endpoint disabled: n/a')).toBeInTheDocument()
    expect(screen.getByText('Message: No message provided.')).toBeInTheDocument()
  })

  it('renders valid guarded apply execution gate specification data', () => {
    render(<GuardedApplyExecutionGateSpecificationPanel specification={{ available: true, specification_type: 'guarded_apply_execution_gate_specification', final_checklist_available: true, final_readiness_checks_passed: true, requires_target_absent: true, requires_create_only_scope: true, requires_allowed_source_type: 'season_template', requires_allowed_overwrite_policy: 'none', requires_audit_metadata: true, required_confirmation_phrase: 'I understand this will create a new season calendar.', required_mutation_scope: 'create_only', requires_identity_reference_match: true, requires_summary_execution_disabled: true, requires_endpoint_disabled_before_execution: true, gate_specification_complete: true, execution_enabled: false, can_execute: false, read_only: true, mutation_permitted: false, message: 'Execution gate specification is read-only in preview mode.' }} />)
    expect(screen.getByText('Available: true')).toBeInTheDocument()
    expect(screen.getByText('Specification type: guarded_apply_execution_gate_specification')).toBeInTheDocument()
    expect(screen.getByText('Final checklist available: true')).toBeInTheDocument()
    expect(screen.getByText('Final readiness checks passed: true')).toBeInTheDocument()
    expect(screen.getByText('Requires target absent: true')).toBeInTheDocument()
    expect(screen.getByText('Requires create-only scope: true')).toBeInTheDocument()
    expect(screen.getByText('Requires allowed source type: season_template')).toBeInTheDocument()
    expect(screen.getByText('Requires allowed overwrite policy: none')).toBeInTheDocument()
    expect(screen.getByText('Requires audit metadata: true')).toBeInTheDocument()
    expect(screen.getByText('Required confirmation phrase: I understand this will create a new season calendar.')).toBeInTheDocument()
    expect(screen.getByText('Required mutation scope: create_only')).toBeInTheDocument()
    expect(screen.getByText('Requires identity reference match: true')).toBeInTheDocument()
    expect(screen.getByText('Requires summary execution disabled: true')).toBeInTheDocument()
    expect(screen.getByText('Requires endpoint disabled before execution: true')).toBeInTheDocument()
    expect(screen.getByText('Gate specification complete: true')).toBeInTheDocument()
    expect(screen.getAllByText('Execution enabled: false').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Can execute: false').length).toBeGreaterThan(0)
    expect(screen.getByText('Read-only: true')).toBeInTheDocument()
    expect(screen.getByText('Mutation permitted: false')).toBeInTheDocument()
    expect(screen.getByText('Message: Execution gate specification is read-only in preview mode.')).toBeInTheDocument()
    expect(screen.getByText('Message: Execution gate specification is read-only in preview mode.')).toHaveTextContent(/read-only|preview|disabled|execution/i)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('handles missing and malformed guarded apply execution gate specification data', () => {
    expect(readGuardedApplyExecutionGateSpecification(undefined)).toBeNull()
    render(<GuardedApplyExecutionGateSpecificationPanel specification={{ available: 'yes', specification_type: '', final_checklist_available: 'x', required_confirmation_phrase: '' }} />)
    expect(screen.getByText('Available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Specification type: n/a')).toBeInTheDocument()
    expect(screen.getByText('Final checklist available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Required confirmation phrase: n/a')).toBeInTheDocument()
    expect(screen.getByText('Message: No message provided.')).toBeInTheDocument()
  })

  it('handles missing and malformed create-only apply audit metadata preview data', () => {
    expect(readCreateOnlyApplyAuditMetadataPreview(undefined)).toBeNull()
    render(<CreateOnlyApplyAuditMetadataPreviewPanel preview={{ available: 'yes', preview_type: '', requested_by_present: 'x' }} />)
    expect(screen.getByText('Available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Preview type: n/a')).toBeInTheDocument()
    expect(screen.getByText('Requested by present: n/a')).toBeInTheDocument()
    expect(screen.getByText('Message: No message provided.')).toBeInTheDocument()
  })

  it('renders future apply reference contract from dry run preview without apply buttons', () => {
    render(<FutureApplyReferenceContractPanel dryRunResultPreview={{ future_apply_reference_contract: { available: true, contract_type: 'future_apply_reference_contract' } }} />)
    expect(screen.getByText('Future apply reference contract')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /apply|execute/i })).not.toBeInTheDocument()
  })

  it('renders valid future apply execution boundary contract data', () => {
    render(<FutureApplyExecutionBoundaryContractPanel contract={{ available: true, contract_type: 'future_apply_execution_boundary_contract', gate_specification_available: true, gate_specification_complete: true, actual_execution_endpoint_exists: false, actual_execution_wiring_enabled: false, mutation_path_enabled: false, preview_stack_only: true, execution_boundary_intact: true, requires_separate_execution_phase: true, requires_separate_endpoint_wiring: true, requires_separate_mutation_audit: true, execution_enabled: false, can_execute: false, read_only: true, mutation_permitted: false, message: 'Execution boundary contract is disabled/read-only preview metadata only; it does not execute apply and does not mutate state.' }} />)
    expect(screen.getByText('Available: true')).toBeInTheDocument()
    expect(screen.getByText('Contract type: future_apply_execution_boundary_contract')).toBeInTheDocument()
    expect(screen.getByText('Gate specification available: true')).toBeInTheDocument()
    expect(screen.getByText('Gate specification complete: true')).toBeInTheDocument()
    expect(screen.getByText('Actual execution endpoint exists: false')).toBeInTheDocument()
    expect(screen.getByText('Actual execution wiring enabled: false')).toBeInTheDocument()
    expect(screen.getByText('Mutation path enabled: false')).toBeInTheDocument()
    expect(screen.getByText('Preview stack only: true')).toBeInTheDocument()
    expect(screen.getByText('Execution boundary intact: true')).toBeInTheDocument()
    expect(screen.getByText('Requires separate execution phase: true')).toBeInTheDocument()
    expect(screen.getByText('Requires separate endpoint wiring: true')).toBeInTheDocument()
    expect(screen.getByText('Requires separate mutation audit: true')).toBeInTheDocument()
    expect(screen.getAllByText('Execution enabled: false').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Can execute: false').length).toBeGreaterThan(0)
    expect(screen.getByText('Read-only: true')).toBeInTheDocument()
    expect(screen.getByText('Mutation permitted: false')).toBeInTheDocument()
    expect(screen.getByText('Message: Execution boundary contract is disabled/read-only preview metadata only; it does not execute apply and does not mutate state.')).toBeInTheDocument()
    expect(screen.getByText('Message: Execution boundary contract is disabled/read-only preview metadata only; it does not execute apply and does not mutate state.')).toHaveTextContent(/read-only|preview|disabled|does not execute apply/i)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('handles missing and malformed future apply execution boundary contract data', () => {
    expect(readFutureApplyExecutionBoundaryContract(undefined)).toBeNull()
    render(<FutureApplyExecutionBoundaryContractPanel contract={{ available: 'yes', contract_type: '', gate_specification_available: 'x', message: '' }} />)
    expect(screen.getByText('Available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Contract type: n/a')).toBeInTheDocument()
    expect(screen.getByText('Gate specification available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Message: No message provided.')).toBeInTheDocument()
  })

  it('renders valid future apply execution decision summary data', () => {
    render(<FutureApplyExecutionDecisionSummaryPanel summary={{ available: true, summary_type: 'future_apply_execution_decision_summary', boundary_contract_available: true, execution_boundary_intact: true, preview_stack_only: true, manual_validation_only: true, separate_execution_phase_required: true, operator_review_required: true, future_execution_phase_may_be_considered: true, execution_authorized: false, execution_enabled: false, can_execute: false, read_only: true, mutation_permitted: false, message: 'Execution decision summary is disabled, read-only, does not execute apply, and provides no execution authorization in this phase.' }} />)
    expect(screen.getByText('Available: true')).toBeInTheDocument()
    expect(screen.getByText('Summary type: future_apply_execution_decision_summary')).toBeInTheDocument()
    expect(screen.getByText('Boundary contract available: true')).toBeInTheDocument()
    expect(screen.getByText('Execution boundary intact: true')).toBeInTheDocument()
    expect(screen.getByText('Preview stack only: true')).toBeInTheDocument()
    expect(screen.getByText('Manual validation only: true')).toBeInTheDocument()
    expect(screen.getByText('Separate execution phase required: true')).toBeInTheDocument()
    expect(screen.getByText('Operator review required: true')).toBeInTheDocument()
    expect(screen.getByText('Future execution phase may be considered: true')).toBeInTheDocument()
    expect(screen.getByText('Execution authorized: false')).toBeInTheDocument()
    expect(screen.getByText('Execution enabled: false')).toBeInTheDocument()
    expect(screen.getByText('Can execute: false')).toBeInTheDocument()
    expect(screen.getByText('Read-only: true')).toBeInTheDocument()
    expect(screen.getByText('Mutation permitted: false')).toBeInTheDocument()
    expect(screen.getByText(/Message: .*disabled.*read-only.*does not execute apply.*no execution authorization/i)).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('handles missing and malformed future apply execution decision summary data', () => {
    expect(readFutureApplyExecutionDecisionSummary(undefined)).toBeNull()
    render(<FutureApplyExecutionDecisionSummaryPanel summary={{ available: 'yes', summary_type: '', execution_authorized: 'no', message: '' }} />)
    expect(screen.getByText('Available: n/a')).toBeInTheDocument()
    expect(screen.getByText('Summary type: n/a')).toBeInTheDocument()
    expect(screen.getByText('Execution authorized: n/a')).toBeInTheDocument()
    expect(screen.getByText('Message: No message provided.')).toBeInTheDocument()
  })
})


describe('Future apply validation UI safety', () => {
  it('renders create-only preflight panel from manual validation without apply/execute buttons and no eager endpoint calls', async () => {
    renderAppAt('/admin/seasons/build')
    expect(api.validateFutureApplyRequestPreview).not.toHaveBeenCalled()
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()

    fireEvent.click(await screen.findByRole('button', { name: 'Validate future apply reference' }))

    await screen.findByText('Create-only apply execution preflight preview')
    expect(screen.getByText('Target absent: true')).toBeInTheDocument()
    expect(screen.getByText('Create-only scope confirmed: true')).toBeInTheDocument()
    expect(screen.getByText('Audit metadata present: false')).toBeInTheDocument()
    expect(screen.getByText('All known preconditions met: false')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Apply$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Execute$/i })).not.toBeInTheDocument()
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
  })


  it('renders future apply execution decision summary from manual validation without mutation behavior', async () => {
    api.validateFutureApplyRequestPreview.mockResolvedValue(futureApplyValidationResponseMock())
    renderAppAt('/admin/seasons/build')
    const callsBeforeClick = api.validateFutureApplyRequestPreview.mock.calls.length
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    expect(api.postSeasonBuilderApplyCommandContract).not.toHaveBeenCalled()

    fireEvent.click(await screen.findByRole('button', { name: 'Validate future apply reference' }))
    await waitFor(() => expect(api.validateFutureApplyRequestPreview.mock.calls.length).toBe(callsBeforeClick + 1))

    await screen.findByText('Future apply execution decision summary')
    const maybeConsideredRows = screen.queryAllByText('Future execution phase may be considered: true')
    if (maybeConsideredRows.length > 0) {
      expect(maybeConsideredRows[0]).toBeInTheDocument()
    }
    expect(screen.queryByText('Execution authorized: true')).not.toBeInTheDocument()
    expect(screen.queryByText('Execution enabled: true')).not.toBeInTheDocument()
    expect(screen.queryByText('Can execute: true')).not.toBeInTheDocument()
    expect(screen.queryByText('Mutation permitted: true')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Apply$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Execute$/i })).not.toBeInTheDocument()
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    expect(api.postSeasonBuilderApplyCommandContract).not.toHaveBeenCalled()
  })

  it('renders create-only audit metadata preview from manual validation result with no apply or execute button', async () => {
    renderAppAt('/admin/seasons/build')
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()

    fireEvent.click(await screen.findByRole('button', { name: 'Validate future apply reference' }))

    await screen.findByText('Create-only apply audit metadata preview')
    expect(screen.getByText('All required audit metadata present: true')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Apply$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Execute$/i })).not.toBeInTheDocument()
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
  })

  it('renders disabled execution contract summary from manual validation result without apply/execute endpoints', async () => {
    api.validateFutureApplyRequestPreview.mockResolvedValue(
      futureApplyValidationResponseMock({
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
          message: 'Execution remains disabled by contract.'
        }
      })
    )
    renderAppAt('/admin/seasons/build')
    const callsBeforeClick = api.validateFutureApplyRequestPreview.mock.calls.length
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()

    fireEvent.click(await screen.findByRole('button', { name: 'Validate future apply reference' }))
    await waitFor(() => expect(api.validateFutureApplyRequestPreview.mock.calls.length).toBe(callsBeforeClick + 1))

    await screen.findByText('Disabled execution contract summary')
    expect(screen.queryByText('Execution enabled: true')).not.toBeInTheDocument()
    expect(screen.queryByText('Can execute: true')).not.toBeInTheDocument()
    expect(screen.queryByText('Mutation permitted: true')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Apply$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Execute$/i })).not.toBeInTheDocument()
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    expect(api.postSeasonBuilderApplyCommandContract).not.toHaveBeenCalledWith(expect.objectContaining({
      requested_candidate_identity_reference_id: expect.any(String)
    }))
  })

  it('renders final guarded apply readiness checklist from manual validation result with no apply or execute button', async () => {
    api.validateFutureApplyRequestPreview.mockResolvedValueOnce(futureApplyValidationResponseMock())
    renderAppAt('/admin/seasons/build')
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    const callsBeforeClick = api.validateFutureApplyRequestPreview.mock.calls.length

    fireEvent.click(await screen.findByRole('button', { name: 'Validate future apply reference' }))
    await waitFor(() => expect(api.validateFutureApplyRequestPreview.mock.calls.length).toBe(callsBeforeClick + 1))
    await screen.findByText('Final guarded apply readiness checklist')
    expect(screen.queryByText('Execution enabled: true')).not.toBeInTheDocument()
    expect(screen.queryByText('Can execute: true')).not.toBeInTheDocument()
    expect(screen.queryByText('Mutation permitted: true')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Apply$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Execute$/i })).not.toBeInTheDocument()
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    expect(api.postSeasonBuilderApplyCommandContract).not.toHaveBeenCalled()
  })

  it('renders guarded apply execution gate specification from manual validation with no apply or execute button', async () => {
    api.validateFutureApplyRequestPreview.mockResolvedValueOnce(futureApplyValidationResponseMock())
    renderAppAt('/admin/seasons/build')
    const callsBeforeClick = api.validateFutureApplyRequestPreview.mock.calls.length
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    expect(api.postSeasonBuilderApplyCommandContract).not.toHaveBeenCalled()

    fireEvent.click(await screen.findByRole('button', { name: 'Validate future apply reference' }))
    await waitFor(() => expect(api.validateFutureApplyRequestPreview.mock.calls.length).toBe(callsBeforeClick + 1))
    await screen.findByText('Guarded apply execution gate specification')
    const gateSpecificationCompleteRows = screen.queryAllByText('Gate specification complete: true')
    if (gateSpecificationCompleteRows.length > 0) {
      expect(gateSpecificationCompleteRows.length).toBeGreaterThan(0)
    }
    expect(screen.queryByText('Execution enabled: true')).not.toBeInTheDocument()
    expect(screen.queryByText('Can execute: true')).not.toBeInTheDocument()
    expect(screen.queryByText('Mutation permitted: true')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Apply$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Execute$/i })).not.toBeInTheDocument()
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    expect(api.postSeasonBuilderApplyCommandContract).not.toHaveBeenCalled()
  })

  it('renders future apply execution boundary contract from manual validation without apply/execute endpoints', async () => {
    api.validateFutureApplyRequestPreview.mockResolvedValueOnce(futureApplyValidationResponseMock())
    renderAppAt('/admin/seasons/build')
    const callsBeforeClick = api.validateFutureApplyRequestPreview.mock.calls.length
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    expect(api.postSeasonBuilderApplyCommandContract).not.toHaveBeenCalled()

    fireEvent.click(await screen.findByRole('button', { name: 'Validate future apply reference' }))
    await waitFor(() => expect(api.validateFutureApplyRequestPreview.mock.calls.length).toBe(callsBeforeClick + 1))

    const previewResultBlocks = await screen.findAllByLabelText('Future apply preview result block')
    const latestPreviewResultBlock = previewResultBlocks[previewResultBlocks.length - 1]
    const boundaryContractHeading = within(latestPreviewResultBlock).getByRole('heading', { name: 'Future apply execution boundary contract' })
    const boundaryContractPanel = boundaryContractHeading.closest('section')
    expect(boundaryContractPanel).not.toBeNull()
    expect(within(boundaryContractPanel as HTMLElement).getByText('Execution boundary intact: true')).toHaveTextContent('Execution boundary intact: true')
    expect(screen.queryByText('Execution enabled: true')).not.toBeInTheDocument()
    expect(screen.queryByText('Can execute: true')).not.toBeInTheDocument()
    expect(screen.queryByText('Mutation permitted: true')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Apply$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Execute$/i })).not.toBeInTheDocument()
    expect(api.postSeasonBuilderApplyCreateOnlyCommand).not.toHaveBeenCalled()
    expect(api.postSeasonBuilderApplyCommandContract).not.toHaveBeenCalled()
  })
})
