import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

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
  getCategories: vi.fn(),
  getTournaments: vi.fn(),
  getTourSeasonsValidation: vi.fn(),
  postSeasonBuilderPreflight: vi.fn(),
  postSeasonBuilderDryRunBuild: vi.fn(),
  postSeasonBuilderApplyCommandContract: vi.fn(),
  postSeasonBuilderApplyCreateOnlyReadiness: vi.fn(),
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

describe('Module 17 pages through routes', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRuns.mockResolvedValue({ runs: [] })
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
        placeholder: 'Event-level additions/replacements/conflicts remain planned for a future phase.'
      },
      validation_warnings: [],
      validation_errors: ['Explicit overwrite/merge policy is required before any future build when a target calendar already exists.'],
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
        identity_readiness: { status: 'blocked_reference', items: [{ area: 'validation_summary', status: 'Blocked', message: "Validation summary status is 'blocking'." }, { area: 'mutation_state', status: 'Blocked', message: 'Mutation remains disabled; this checklist is reference-only.' }], future_command_reference: { preflight_fingerprint: payload.preflight_fingerprint, reviewed_diff_id: payload.reviewed_diff_id, dry_run_result_fingerprint: 'drf_test_existing', dry_run_result_id: 'drr_test_existing', can_reference_future_command: false, mutation_still_disabled: true } },
        dry_run_result_fingerprint: 'drf_test_existing',
        dry_run_result_id: 'drr_test_existing'
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
  it('renders Tour & Seasons hub and shell routes while keeping operational routes available', async () => {
    renderAppAt('/admin/tour-seasons')
    expect(await screen.findByRole('heading', { name: 'Tour & Seasons' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Categories/ })).toHaveAttribute('href', '/admin/tour-seasons/categories')
    expect(screen.getByRole('link', { name: /Tournaments/ })).toHaveAttribute('href', '/admin/tour-seasons/tournaments')
    expect(screen.getByRole('link', { name: /Season Templates/ })).toHaveAttribute('href', '/admin/tour-seasons/season-templates')
    expect(screen.getByRole('link', { name: /Season Registry/ })).toHaveAttribute('href', '/admin/tour-seasons/season-registry')
    expect(screen.getByRole('link', { name: /Seasons Concrete 61-week season calendars/ })).toHaveAttribute('href', '/admin/seasons')
    expect(screen.getByRole('link', { name: /Calendar Compare \/ Apply/ })).toHaveAttribute('href', '/admin/tour-seasons/compare')
    expect(screen.getByRole('link', { name: /Calendar Validation/ })).toHaveAttribute('href', '/admin/tour-seasons/validation')

    renderAppAt('/admin/tour-seasons/categories')
    expect(await screen.findByRole('heading', { name: 'Categories' })).toBeInTheDocument()
    expect(screen.getAllByText(/Read-only foundation\./).length).toBeGreaterThan(0)
    expect(await screen.findByRole('link', { name: /GOLD \(gold\)/ })).toHaveAttribute('href', '/admin/tour-seasons/categories/gold')
    expect(screen.getAllByRole('link', { name: 'Open Tournament Templates' })[0]).toHaveAttribute('href', '/admin/tournament-templates')
    expect(screen.getAllByRole('link', { name: 'Open Season Templates' })[0]).toHaveAttribute('href', '/admin/tour-seasons/season-templates')

    renderAppAt('/admin/tour-seasons/tournaments')
    expect(await screen.findByRole('heading', { name: 'Tournaments' })).toBeInTheDocument()
    expect(screen.getByText(/Read-only tournament master records derived from current tournament template config\./)).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: /World Tour Gold \(world-tour-gold\)/ })).toHaveAttribute('href', '/admin/tour-seasons/tournaments/world-tour-gold')
    expect(screen.getAllByRole('link', { name: 'Open Tournament Templates' })[0]).toHaveAttribute('href', '/admin/tournament-templates')
    expect(screen.getByRole('link', { name: 'Open Categories' })).toHaveAttribute('href', '/admin/tour-seasons/categories')
    expect(screen.getAllByRole('link', { name: 'Open Season Templates' })[0]).toHaveAttribute('href', '/admin/tour-seasons/season-templates')


    renderAppAt('/admin/tour-seasons/season-templates')
    expect(await screen.findByRole('heading', { name: 'Season Templates' })).toBeInTheDocument()
    expect(screen.getAllByText(/Read-only foundation\./).length).toBeGreaterThan(0)
    expect((await screen.findAllByText(/Source path: config\/tournament_templates\/mvp_templates\.json/)).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Default MSA Template Preview \(default_msa_template_preview\)/ })).toHaveAttribute('href', '/admin/tour-seasons/season-templates/default_msa_template_preview')
    expect(screen.getAllByRole('link', { name: 'Open Season Registry' }).some((link) => link.getAttribute('href') === '/admin/tour-seasons/season-registry')).toBe(true)
    expect(screen.getByRole('link', { name: 'Open Seasons' })).toHaveAttribute('href', '/admin/seasons')


    renderAppAt('/admin/tour-seasons/season-registry')
    expect(await screen.findByRole('heading', { level: 2, name: 'Season Registry' })).toBeInTheDocument()
    expect(screen.getByText(/fixed 2000\/01–2039\/40 MSA season model\./)).toBeInTheDocument()
    const seasonLink = await screen.findByRole('link', { name: '2000/01' })
    expect(seasonLink).toHaveAttribute('href', '/admin/seasons/detail/2000%2F01')
    expect(screen.getByRole('cell', { name: '2039/40' })).toBeInTheDocument()
    expect(screen.getByText(/SW1 → YW37/)).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Season' })).toBeInTheDocument()
    expect(screen.getByText('Season links open the read-only Concrete Season detail profile. Direct season editing workflow is planned.')).toBeInTheDocument()

    renderAppAt('/admin/tour-seasons/compare')
    expect(await screen.findByRole('heading', { name: 'Calendar Compare / Apply' })).toBeInTheDocument()
    expect(screen.getByText(/Read-only comparison foundation for templates, registry seasons, and future concrete season calendars\./)).toBeInTheDocument()
    expect(await screen.findByText('Registry range')).toBeInTheDocument()
    expect(await screen.findByText('2000/01–2039/40')).toBeInTheDocument()
    expect(screen.getByText('Registry season count')).toBeInTheDocument()
    expect(screen.getByText('Registry week count')).toBeInTheDocument()
    expect(screen.getByText('Season templates count')).toBeInTheDocument()
    expect(screen.getAllByText('Default MSA Template Preview').length).toBeGreaterThan(0)
    expect(screen.getByText('Planned statuses: Same, Modified, Missing from current, Only in current, and Conflict.')).toBeInTheDocument()
    expect(screen.getByText('Planned actions: Apply to this season, Replace current, Keep current, Ignore, and Open editor.')).toBeInTheDocument()
    expect(screen.getByText('These actions are planned and not enabled.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /apply|replace|keep current|ignore|open editor|save|update|delete|create/i })).not.toBeInTheDocument()

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
  })

  it('renders Season Builder read-only source selection preview', async () => {
    renderAppAt('/admin/seasons/build')
    expect(await screen.findByRole('heading', { name: 'Season Builder' })).toBeInTheDocument()
    expect(screen.getByText('Read-only preflight foundation for future season creation workflows.')).toBeInTheDocument()
    expect(screen.getByText('This page does not build or modify calendars.')).toBeInTheDocument()
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
    expect(screen.getByText('Target existing calendar preview')).toBeInTheDocument()
    expect(screen.getByText('Overwrite / merge policy preview')).toBeInTheDocument()
    expect(screen.getByText('Overwrite / merge policy selection for preflight')).toBeInTheDocument()
    expect(screen.getByText('Read-only preflight input. This selector only changes the backend preflight payload and does not execute merge or overwrite.')).toBeInTheDocument()
    expect(screen.getByLabelText('Future policy preview')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'No policy selected' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Merge policy preview' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Overwrite policy preview' })).toBeInTheDocument()
    expect(await screen.findByText('Existing target calendar detected. Backend preflight will require an explicit future policy before any future build can be considered.')).toBeInTheDocument()
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
    expect(screen.getByText('audit_preview')).toBeInTheDocument()
    expect(screen.getByText('Future implementation must add an authoritative backend preflight before any build, merge, overwrite, or apply command can exist.')).toBeInTheDocument()
    expect(screen.getByText('Backend preflight result')).toBeInTheDocument()
    expect(await screen.findByText('Even when backend preflight succeeds, build actions remain unavailable in this phase.')).toBeInTheDocument()
    expect(screen.getByText('Policy preview interpretation')).toBeInTheDocument()
    expect(screen.getByText('No overwrite/merge policy is selected for this read-only preflight.')).toBeInTheDocument()
    expect(screen.getByText('Policy preview never enables build actions in this phase.')).toBeInTheDocument()
    expect(screen.getByText('Status: Blocked in this phase')).toBeInTheDocument()
    expect(screen.getByText('Blocking validation errors are present.')).toBeInTheDocument()
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
    expect(await screen.findByText(/Calendar exists/i)).toBeInTheDocument()
    expect(screen.getAllByText('Existing calendar detected.').length).toBeGreaterThan(0)
    expect(screen.getByText('Silent overwrite must never be allowed.')).toBeInTheDocument()
    expect(screen.getByText('Merge/replace choice must be explicit and audited before any future command.')).toBeInTheDocument()
    expect(screen.getByText('Future build command must be explicit, audited, and reviewable.')).toBeInTheDocument()
    expect(screen.getByText('Existing target calendar requires explicit audited overwrite/merge choice before any future build.')).toBeInTheDocument()
    expect(screen.getByText('Review read-only diff and backend validation before any future command.')).toBeInTheDocument()
    expect(screen.getByText('No build, overwrite, merge, or apply command is available from this page.')).toBeInTheDocument()
    expect(screen.getByText('Existing target calendar requires future authoritative backend diff before any overwrite/merge command.')).toBeInTheDocument()
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
    expect(screen.getByText('Existing calendar detected; future build workflow must require explicit overwrite/merge choice.')).toBeInTheDocument()
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
    expect(screen.getByText('audit_reason')).toBeInTheDocument()
    expect(screen.getByText('seed / template_version / config_hash')).toBeInTheDocument()
    expect(screen.getByText('explicit_confirmation')).toBeInTheDocument()
    expect(screen.getByText('reviewed_diff_id or dry_run_result_id')).toBeInTheDocument()
    expect(screen.getByText('mutation_scope')).toBeInTheDocument()
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
    expect((await screen.findAllByText('explicit_confirmation_present')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('conflict_contract_preview_available')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Raw disabled dry-run build contract JSON')).toBeInTheDocument()
    expect(await screen.findByText('Execution remains disabled; this panel is not a build control.')).toBeInTheDocument()
    expect(screen.getByText('Disabled apply command contract result')).toBeInTheDocument()
    expect(screen.getByText('Create-only apply readiness')).toBeInTheDocument()
    expect(screen.getByText('Read-only disabled apply command contract check. This does not build, merge, overwrite, or apply anything.')).toBeInTheDocument()
    expect(screen.getByText('Read-only create-only apply readiness check. This panel does not execute apply or create a calendar.')).toBeInTheDocument()
    expect(screen.getByText('Backend readiness says create-only apply is ready, but this panel is still read-only. No calendar is created from this UI.')).toBeInTheDocument()
    expect(screen.getByText('Safety checklist')).toBeInTheDocument()
    expect(screen.getByText('Real apply endpoint called from UI')).toBeInTheDocument()
    expect(screen.getByText('Mutation hook installed')).toBeInTheDocument()
    expect(screen.getByText('Calendar created by this panel')).toBeInTheDocument()
    expect(screen.getByText('Backend readiness satisfied')).toBeInTheDocument()
    expect(screen.getByText('Audit persisted')).toBeInTheDocument()
    expect(screen.getAllByText('can_mutate').length).toBeGreaterThan(0)
    expect(screen.getAllByText('service_insert_applicable').length).toBeGreaterThan(0)
    expect(screen.getAllByText('false').length).toBeGreaterThan(0)
    expect(screen.getByText('Candidate count: 1')).toBeInTheDocument()
    expect(screen.getByText('Categories count: 1')).toBeInTheDocument()
    expect(screen.getByText('Categories values: GOLD')).toBeInTheDocument()
    expect(screen.getByText('Tour levels count: 1')).toBeInTheDocument()
    expect(screen.getByText('Tour levels values: WORLD_TOUR')).toBeInTheDocument()
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    expect((api as { postSeasonBuilderApplyCreateOnlyCommand?: unknown }).postSeasonBuilderApplyCreateOnlyCommand).toBeUndefined()
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
    await waitFor(() => {
      expect(api.postSeasonBuilderApplyCommandContract).toHaveBeenCalledWith(expect.objectContaining({
        preflight_fingerprint: 'pf_test_existing',
        reviewed_diff_id: 'rd_test_existing',
        dry_run_result_fingerprint: 'drf_test_existing',
        dry_run_result_id: 'drr_test_existing',
        audit_reason: null,
        explicit_confirmation: null,
        mutation_scope: null
      }))
    })
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
    expect(screen.getByText('Validation errors count: 0.')).toBeInTheDocument()
    expect(screen.getByText('Real dry-run generation is not implemented yet.')).toBeInTheDocument()
    expect(screen.getByText('The dry-run contract is visible, but execution remains disabled.')).toBeInTheDocument()
    expect(api.postSeasonBuilderPreflight).toHaveBeenCalledWith({ target_season_label: '2000/01', source_type: 'season_template', source_template_id: 'default_msa_template_preview', overwrite_policy: null, requested_by: 'local-admin-preview' })
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
    expect(api.getSeasonCalendar).toHaveBeenCalledTimes(1)
    expect(screen.getByText('Future audited command flow')).toBeInTheDocument()
    expect(screen.getByText('None of these commands are implemented on this page.')).toBeInTheDocument()
    expect(screen.getByText('Read-only preflight checklist')).toBeInTheDocument()
    expect(screen.getByText('Read-only preflight preview. Not an authoritative build gate.')).toBeInTheDocument()
    const forbiddenMutationActions = ['Build', 'Create', 'Apply', 'Generate', 'Simulate', 'Run', 'Save', 'Update', 'Delete', 'Bootstrap', 'Merge', 'Overwrite', 'Preflight']
    for (const action of forbiddenMutationActions) {
      expect(screen.queryByRole('button', { name: new RegExp(`^${action}$`, 'i') })).not.toBeInTheDocument()
    }
  }, 20000)

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
      source_type: 'season_template',
      source_template_id: 'default_msa_template_preview',
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
        placeholder: 'Event-level additions/replacements/conflicts remain planned for a future phase.'
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
      source_type: 'season_template',
      source_template_id: 'default_msa_template_preview',
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
        identity_readiness: { status: 'ready_reference', items: [{ area: 'preflight_fingerprint', status: 'OK', message: 'Preflight fingerprint is present.' }], future_command_reference: { preflight_fingerprint: 'pf_test_empty', reviewed_diff_id: 'rd_test_empty', dry_run_result_fingerprint: 'drf_test_empty', dry_run_result_id: 'drr_test_empty', can_reference_future_command: true, mutation_still_disabled: true } }
      },
      message: 'Dry-run build command contract exists, but execution is disabled in this phase.'
    })
    api.postSeasonBuilderApplyCommandContract.mockResolvedValueOnce({
      command: 'season_builder_apply_command',
      enabled: false,
      can_execute: false,
      can_mutate: false,
      target_season_label: '2000/01',
      source_type: 'season_template',
      source_template_id: 'default_msa_template_preview',
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
    expect(screen.getByText('ready_reference')).toBeInTheDocument()
    expect(screen.getByText('can_reference_future_command')).toBeInTheDocument()
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
    expect(screen.getByText('season_week')).toBeInTheDocument()
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
    expect(screen.getByRole('link', { name: 'Open Categories' })).toHaveAttribute('href', '/admin/tour-seasons/categories')
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
    expect(screen.getByRole('link', { name: 'Open Categories' })).toHaveAttribute('href', '/admin/tour-seasons/categories')
    expect(screen.getByRole('link', { name: 'Open Seasons' })).toHaveAttribute('href', '/admin/seasons')

    renderAppAt('/admin/tour-seasons/season-templates/unknown-id')
    expect(await screen.findByText('Season template not found.')).toBeInTheDocument()
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
    expect(screen.getByRole('link', { name: /Countries Edit country inputs/i })).toHaveAttribute('href', '/admin/world/countries')
    expect(screen.getByRole('link', { name: /Talent Preview Preview expected Elite Talents/i })).toHaveAttribute('href', '/admin/world/talent-preview')
    expect(screen.queryByRole('link', { name: 'Country Momentum' })).not.toBeInTheDocument()
  })

  it('renders country detail route for existing country code', async () => {
    renderAppAt('/admin/world/countries/EGY')
    expect(await screen.findByRole('heading', { name: 'Egypt (EGY)' })).toBeInTheDocument()
    expect(screen.getByText(/Country profile and authored model inputs/i)).toBeInTheDocument()
  })

  it('renders the Viewer MSA home route with no active run empty state', async () => {
    localStorage.removeItem('beta_engine:viewer_active_run_id')
    api.listRuns.mockResolvedValueOnce({ runs: [] })
    renderAppAt('/viewer')
    expect(await screen.findByRole('heading', { name: 'MSA Website Home' })).toBeInTheDocument()
    expect(screen.getByText('Select a Viewer run first to enable run-scoped MSA website links.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Rankings' })).toHaveAttribute('href', '/viewer/rankings')
    expect(screen.queryByRole('link', { name: 'Players' })).toHaveAttribute('href', '/viewer/players')
    expect(screen.queryByRole('link', { name: 'Countries' })).toHaveAttribute('href', '/viewer/countries')
    expect(screen.queryByRole('link', { name: 'History' })).toHaveAttribute('href', '/viewer/history')
    expect(screen.queryByRole('link', { name: 'Finals' })).not.toBeInTheDocument()
  })

  it('renders the Viewer MSA home route with active run links', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'viewer-run-1')
    api.listRuns.mockResolvedValueOnce({ runs: [] })
    renderAppAt('/viewer')
    expect(await screen.findByRole('heading', { name: 'MSA Website Home' })).toBeInTheDocument()
    expect(screen.getAllByText(/viewer-run-1/)[0]).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Rankings' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/rankings')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Tournaments' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/tournaments')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Players' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/players')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Countries' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/countries')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'History' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/history')).toBe(true)
  })

  it('renders top-level Viewer rankings with active run link', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'viewer-run-2')
    renderAppAt('/viewer/rankings')
    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Rankings' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-2/rankings')).toBe(true)
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
})
