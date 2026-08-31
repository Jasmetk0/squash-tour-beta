export type HealthResponse = { status: 'ok' }

export type SeasonRegistryEntry = {
  season_start_year: number
  label: string
  season_index: number
  week_count: number
  season_week_start: number
  season_week_end: number
  year_week_start: number
  year_week_end: number
  status: string
}

export type SeasonRegistryResponse = {
  start_season: string
  end_season: string
  season_count: number
  week_count: number
  season_week_1_year_week: number
  seasons: SeasonRegistryEntry[]
}

export type SeasonTemplateSlot = {
  slot_id: string
  season_week_start: number
  season_week_end: number
  duration_weeks: number
  tournament_name: string
  category: string
  host_country: string | null
  region: string | null
  has_qualification: boolean
  qualifying_week_start: number | null
  main_draw_week_start: number | null
  source_template_id: string | null
  notes: string | null
}

export type SeasonTemplateSummary = {
  template_id: string
  name: string
  description: string
  season_count_supported: number | null
  week_count: number
  slot_count: number
  source: string
  status: string
  slots: SeasonTemplateSlot[]
}


export type CategorySummary = {
  category_id: string
  name: string
  status: 'read_only_foundation'
  source: string
  template_count: number
  valid_from_season: string | null
  valid_to_season: string | null
  tour_level: string | null
  prestige_rank: number | null
  mandatory: boolean | null
  main_draw_size: number | null
  qualification_draw_size: number | null
  direct_entries: number | null
  qualifiers: number | null
  wildcards: number | null
  lucky_losers: number | null
  seeds_count: number | null
  points_by_round: Record<string, number> | null
  prize_money_total: number | null
  match_format: string | null
  qualifying_weeks_count: number | null
  main_draw_weeks_count: number | null
  schedule_footprint_weeks: number | null
  source_template_ids: string[]
  notes: string[]
}

export type CategoriesResponse = {
  categories: CategorySummary[]
  source_path: string | null
  status: 'read_only_foundation'
}

export type TournamentMasterSummary = {
  tournament_id: string
  name: string
  status: 'read_only_foundation'
  source: string
  source_template_ids: string[]
  template_count: number
  categories: string[]
  tour_levels: string[]
  host_countries: string[]
  regions: string[]
  default_category: string | null
  default_host_country: string | null
  default_region: string | null
  default_duration_weeks: number | null
  has_qualification: boolean | null
  notes: string[]
}


export type TourSeasonsValidationSeverity = 'ok' | 'info' | 'warning'

export type TourSeasonsValidationIssue = {
  issue_id: string
  severity: TourSeasonsValidationSeverity
  area: string
  item_id: string | null
  item_name: string | null
  message: string
  link_hint: string | null
}

export type TourSeasonsValidationSection = {
  section_id: string
  title: string
  issues: TourSeasonsValidationIssue[]
}

export type TourSeasonsValidationSummary = {
  total_checks: number
  warning_count: number
  info_count: number
  ok_count: number
  registry_loaded: boolean
  category_count: number
  tournament_count: number
  season_template_count: number
  season_template_slot_count: number
}

export type TourSeasonsValidationResponse = {
  status: 'read_only_foundation'
  summary: TourSeasonsValidationSummary
  sections: TourSeasonsValidationSection[]
  planned_future: string[]
}

export type TournamentMastersResponse = {
  tournaments: TournamentMasterSummary[]
  source_path: string | null
  status: 'read_only_foundation'
}


export type SeasonTemplatesResponse = {
  templates: SeasonTemplateSummary[]
  source_path: string | null
  status: string
}

export type CalendarTemplateEventRecord = {
  id: string
  name: string
  category_code: string
  weeks: number[]
  qualification_weeks: number[]
  locked: boolean
  country_code?: string | null
  city?: string | null
  venue?: string | null
  notes?: string | null
  source_template_id?: string | null
  event_fingerprint?: string | null
}


export type CalendarTemplateComparePolicy = 'replace_unlocked_only' | 'copy_missing_only'
export type CalendarTemplateCompareTargetSource = 'payload' | 'planning_calendar'

export type CalendarTemplateCompareStatus =
  | 'same'
  | 'missing_from_target'
  | 'only_in_target'
  | 'conflict'
  | 'locked_target_preserved'

export type CalendarTemplateCompareDryRunRequest = {
  target_season_label: string
  source_template_id: string
  target_source?: CalendarTemplateCompareTargetSource
  target_events?: CalendarTemplateEventRecord[]
  selected_source_event_ids?: string[] | null
  policy: CalendarTemplateComparePolicy
}

export type CalendarTemplateCompareSummary = {
  same_count: number
  missing_from_target_count: number
  only_in_target_count: number
  conflict_count: number
  locked_target_preserved_count: number
  selected_source_event_count: number
  source_event_count: number
  target_event_count: number
}

export type CalendarTemplateCompareItem = {
  status: CalendarTemplateCompareStatus
  source_event_id?: string | null
  target_event_id?: string | null
  event_name: string
  category_code: string
  source_weeks?: number[] | null
  target_weeks?: number[] | null
  source_qualification_weeks?: number[] | null
  target_qualification_weeks?: number[] | null
  locked_target: boolean
  reason: string
}

export type CalendarTemplateCompareSafety = {
  read_only: boolean
  mutation_performed: boolean
  apply_endpoint_enabled: boolean
  message: string
}


export type PlanningCalendarApplyTemplatePolicy = 'copy_missing_only'

export type PlanningCalendarApplyTemplateCommandRequest = {
  source_template_id: string
  policy: PlanningCalendarApplyTemplatePolicy
  selected_source_event_ids?: string[] | null
  expected_planning_calendar_fingerprint: string
  source_template_fingerprint: string
  reviewed_diff_fingerprint: string
  requested_by: string
  audit_reason: string
  explicit_confirmation: string
  idempotency_key?: string | null
}

export type PlanningCalendarApplyTemplateCommandResponse = {
  command: string
  applied: boolean
  mutation_performed: boolean
  target_season_label: string
  normalized_target_season_label: string
  source_template_id: string
  policy: PlanningCalendarApplyTemplatePolicy
  audit_record_id: string | null
  audit_record_fingerprint: string | null
  audit_persisted: boolean
  audit_persistence_status: string
  before_calendar_fingerprint: string | null
  after_calendar_fingerprint: string | null
  source_template_fingerprint: string
  reviewed_diff_fingerprint: string
  recomputed_diff_fingerprint: string | null
  apply_plan_fingerprint: string | null
  applied_event_count: number
  created_event_count: number
  updated_event_count: number
  preserved_locked_event_count: number
  skipped_event_count: number
  rejected_event_count: number
  created_items: unknown[]
  updated_items: unknown[]
  preserved_locked_items: unknown[]
  skipped_items: unknown[]
  rejected_items: unknown[]
  validation_errors: string[]
  validation_warnings: string[]
  safety_summary: Record<string, unknown> | string | null
  message: string
}

export type CalendarTemplateCompareDryRunResponse = {
  dry_run: boolean
  mutation_performed: boolean
  target_season_label: string
  source_template_id: string
  policy: CalendarTemplateComparePolicy
  target_source: CalendarTemplateCompareTargetSource
  source_template_fingerprint?: string | null
  target_fingerprint: string
  target_calendar_fingerprint?: string | null
  target_calendar_exists?: boolean
  diff_fingerprint: string
  summary: CalendarTemplateCompareSummary
  items: CalendarTemplateCompareItem[]
  safety: CalendarTemplateCompareSafety
  status: string
}


export type PlanningCalendarSafetyResponse = {
  planning_only: boolean
  viewer_visible: boolean
  simulation_consumed: boolean
  canonical_season_calendar_modified: boolean
}

export type PlanningCalendarEventRecord = {
  id: string
  name: string
  category_code: string
  weeks: number[]
  qualification_weeks: number[]
  locked: boolean
  country_code?: string | null
  city?: string | null
  venue?: string | null
  notes?: string | null
  source_template_id?: string | null
  source_template_fingerprint?: string | null
  source_template_event_id?: string | null
  source_template_event_fingerprint?: string | null
  event_fingerprint?: string | null
  apply_metadata?: Record<string, unknown> | null
}

export type PlanningSeasonCalendarRecord = {
  season_label: string
  normalized_season_label: string
  status: 'draft' | 'active' | 'archived'
  events: PlanningCalendarEventRecord[]
  metadata: Record<string, unknown>
  calendar_fingerprint?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type PlanningSeasonCalendarListResponse = {
  calendars: PlanningSeasonCalendarRecord[]
  source_path: string | null
  schema_version: 'planning_season_calendars.v1'
  registry_fingerprint: string | null
  read_only: boolean
  status: 'ok'
  safety: PlanningCalendarSafetyResponse
}

export type PlanningSeasonCalendarDetailResponse = {
  calendar: PlanningSeasonCalendarRecord | null
  source_path: string | null
  schema_version: 'planning_season_calendars.v1'
  registry_fingerprint: string | null
  read_only: boolean
  status: 'ok'
  safety: PlanningCalendarSafetyResponse
}

export type CalendarTemplateUpsertPayload = {
  id: string
  name: string
  description: string
  status: 'draft' | 'active' | 'archived'
  events: CalendarTemplateEventRecord[]
}

export type CalendarTemplateRecord = {
  id: string
  name: string
  description: string
  status: 'draft' | 'active' | 'archived'
  created_at?: string | null
  updated_at?: string | null
  events: CalendarTemplateEventRecord[]
  template_fingerprint?: string | null
}

export type CalendarTemplateListResponse = {
  templates: CalendarTemplateRecord[]
  source_path?: string | null
  status: string
  schema_version: string
}

export type CalendarTemplateDetailResponse = {
  template: CalendarTemplateRecord | null
  source_path?: string | null
  status: string
  schema_version: string
}

export type SeasonTemplateValidationIssue = {
  severity: 'warning' | 'error'
  code: string
  message: string
  slot_id?: string | null
}

export type SeasonTemplateSlotValidationSummary = {
  status: 'clean' | 'warnings' | 'errors'
  error_count: number
  warning_count: number
  issue_count: number
  slot_count: number
  week_count?: number | null
  first_week?: number | null
  last_week?: number | null
}

export type SeasonTemplateSlotValidationResponse = {
  template_id: string
  template_exists: boolean
  read_only: boolean
  summary: SeasonTemplateSlotValidationSummary
  issues: SeasonTemplateValidationIssue[]
  message: string
}


export type SeasonTemplateSlotConflict = {
  severity: 'warning' | 'info'
  code: string
  message: string
  season_week?: number | null
  slot_ids?: string[]
  categories?: string[]
  tour_levels?: string[]
  host_countries?: string[]
  read_only?: boolean
}

export type SeasonTemplateSlotConflictSummary = {
  status: 'clean' | 'warnings' | 'info'
  warning_count: number
  info_count: number
  conflict_count: number
  slot_count: number
  occupied_week_count: number
  busiest_week?: number | null
  busiest_week_slot_count?: number | null
  read_only?: boolean
}

export type SeasonTemplateSlotConflictReportResponse = {
  template_id: string
  template_exists: boolean
  read_only: boolean
  summary: SeasonTemplateSlotConflictSummary
  conflicts: SeasonTemplateSlotConflict[]
  template_conflict_diagnostics_overview?: SeasonTemplateConflictDiagnosticsOverview | null
  message: string
}

export type SeasonTemplateSlotConflictCodeMetadata = {
  code: string
  severity: 'warning' | 'info'
  title: string
  description: string
  read_only: boolean
}

export type SeasonTemplateSlotConflictCodeRegistryResponse = {
  codes: SeasonTemplateSlotConflictCodeMetadata[]
  code_count: number
  read_only: boolean
  message: string
}

export type SeasonTemplateConflictDiagnosticsOverview = {
  selected_report_available?: boolean
  selected_status?: string | null
  selected_conflict_count?: number
  preflight_preview_available?: boolean
  preflight_summary_available?: boolean
  preflight_status?: string | null
  preflight_conflict_count?: number
  dry_run_preview_available?: boolean
  dry_run_summary_available?: boolean
  dry_run_status?: string | null
  dry_run_conflict_count?: number
  mutation_behavior?: string
  blocking_behavior?: string
  read_only?: boolean
  non_blocking?: boolean
}

export type SeasonTemplateSlotValidationIssueCodeMetadata = {
  code: string
  severity: 'warning' | 'error'
  title: string
  description: string
  field?: string | null
  read_only: boolean
}

export type SeasonTemplateSlotValidationIssueCodeRegistryResponse = {
  codes: SeasonTemplateSlotValidationIssueCodeMetadata[]
  code_count: number
  read_only: boolean
  message: string
}

export type RunSummary = {
  run_id: string
  season: number
  seed: number
  config_version: string | null
  config_fingerprint: string | null
  world_id: string
  next_event_index: number
  total_events: number
  completed_event_ids: string[]
}

export type RunContainer = {
  run_id: string
  display_name: string | null
  storage_kind: 'built_in' | 'custom_local'
  read_only: boolean
  world_id: string | null
  world_package_fingerprint: string | null
  config_version: string | null
  config_fingerprint: string | null
  global_seed: number | null
  timeline_start_season: number
  timeline_end_season: number
  viewer_branch_id?: string | null
  official_branch_id: string | null
  status: string
  metadata_json: Record<string, unknown>
  mapped_simulation_run_count: number
}

export type RunContainerListResponse = {
  run_containers: RunContainer[]
}

export type RunBranch = {
  branch_id: string
  run_id: string
  display_name: string
  status: string
  read_only: boolean
  branch_seed: number | null
  forked_from_branch_id: string | null
  forked_from_checkpoint_id: string | null
  forked_from_saved_revision_id?: string | null
  saved_head_revision_id?: string | null
  head_checkpoint_id: string | null
  legacy_simulation_run_id: string | null
  metadata_json: Record<string, unknown>
  is_viewer_branch?: boolean
  is_official: boolean
}

export type RunBranchListResponse = { run_branches: RunBranch[] }

export type CreateRunBranchFromSavedRevisionRequest = {
  source_branch_id: string
  source_saved_revision_id: string
  display_name?: string
}

export type ViewerBranchWorkingDraft = {
  run_id: string
  branch_id: string
  draft_id: string
  base_saved_revision_id: string
  saved_viewer_branch_id: string
  proposed_viewer_branch_id: string
  current_viewer_branch_id: string
  status: 'clean' | 'dirty'
  change_count: number
  draft_version: number
  can_save: boolean
}

export type SavedRevision = {
  revision_id: string
  sequence: number
  parent_revision_id: string | null
  kind: string
  payload_schema_version: string
  content_hash_algorithm: string
  content_hash: string
  change_summary: Record<string, unknown>
}

export type SavedRevisionHistoryEntry = SavedRevision & {
  revision_branch_id: string
  created_at: string | null
  is_shared_revision: boolean
  is_branch_head: boolean
}

export type SavedRevisionHistoryDetail = SavedRevisionHistoryEntry & {
  run_id: string
  branch_id: string
  payload: Record<string, unknown>
}

export type SavedRevisionHistoryResponse = {
  run_id: string
  branch_id: string
  saved_head_revision_id: string
  saved_revisions: SavedRevisionHistoryEntry[]
}

export type SavedRevisionRecoveryCheckpoint = {
  checkpoint_id: string
  run_id: string
  branch_id: string
  saved_revision_id: string
  target_saved_revision_id: string
  restore_saved_revision_id: string
  kind: 'pre_restore_saved_revision'
  draft_id: string
  draft_version: number
  viewer_branch_id: string
  content_hash_algorithm: string
  content_hash: string
  created_at: string | null
}

export type SavedRevisionAuditEvent = {
  audit_event_id: string
  run_id: string
  branch_id: string
  saved_revision_id: string
  event_kind: string
  payload: Record<string, unknown>
  created_at: string | null
}

export type SavedRevisionRecoveryActivityResponse = {
  run_id: string
  branch_id: string
  saved_head_revision_id: string
  safety_checkpoints: SavedRevisionRecoveryCheckpoint[]
  audit_events: SavedRevisionAuditEvent[]
}

export type RestoreSavedRevisionRequest = {
  expected_head_saved_revision_id: string
  expected_draft_version: number
  expected_current_viewer_branch_id: string
  explicit_confirmation: boolean
}

export type SavedRevisionRestoreCheckpoint = {
  checkpoint_id: string
  saved_revision_id: string
  target_saved_revision_id: string
  restore_saved_revision_id: string
  kind: 'pre_restore_saved_revision'
  draft_id: string
  draft_version: number
  viewer_branch_id: string
  content_hash_algorithm: string
  content_hash: string
}

export type RestoreSavedRevisionResponse = {
  run_id: string
  branch_id: string
  previous_saved_head_revision_id: string
  target_saved_revision_id: string
  previous_viewer_branch_id: string
  viewer_branch_id: string
  safety_checkpoint: SavedRevisionRestoreCheckpoint
  saved_revision: SavedRevision
  working_draft: ViewerBranchWorkingDraft
  audit_event_id: string
}

export type BranchCheckpoint = {
  checkpoint_id: string; run_id: string; branch_id: string; parent_checkpoint_id: string | null; sequence: number; kind: string; season: number
  week: number | null; event_id: string | null; event_sequence: number | null; command_id: string; command_kind: string; command_boundary: string
  config_version: string | null; config_fingerprint: string | null; world_id: string; world_fingerprint: string | null; global_seed: number | null; branch_seed: number | null
  seed_namespace: Record<string, unknown>; payload_schema_version: string; content_hash_algorithm: string; content_hash: string; payload: Record<string, unknown>
}
export type BranchCheckpointListResponse = { branch_checkpoints: BranchCheckpoint[] }
export type CaptureInitialBranchCheckpointRequest = { simulation_run_id: string; command_id?: string | null }
export type CaptureSeasonRolloverBranchCheckpointRequest = { simulation_run_id: string; from_season?: number | null; to_season?: number | null; command_id?: string | null }
export type CaptureBootstrapStartBranchCheckpointRequest = { simulation_run_id: string; source_run_id?: string | null; from_season?: number | null; to_season?: number | null; command_id?: string | null }
export type CaptureCurrentBranchCheckpointRequest = { simulation_run_id: string; command_id?: string | null }
export type CaptureCompletedEventBranchCheckpointRequest = { simulation_run_id: string; event_id?: string | null; event_sequence?: number | null; command_id?: string | null }
export type CaptureCompletedWeekBranchCheckpointRequest = { simulation_run_id: string; week: number; command_id?: string | null }
export type CaptureAdminActionBranchCheckpointRequest = { simulation_run_id: string; action_id?: string | null; action_sequence?: number | null; command_id?: string | null }
export type BranchState = {
  branch_id: string; run_id: string; head_checkpoint_id: string | null
  current_season: number | null; current_week: number | null; current_event_id: string | null; current_event_sequence: number | null
  state_schema_version: string; status: string; metadata_json: Record<string, unknown>
}
export type BranchStateListResponse = { branch_states: BranchState[] }

export type AdminForkRunBranchRequest = {
  source_branch_id: string; source_checkpoint_id: string; target_branch_id: string; target_branch_display_name: string
  target_legacy_simulation_run_id: string; target_branch_seed: number; command_id: string
}
export type AdminForkRunBranchResponse = {
  product_run_id: string; source_branch_id: string; source_checkpoint_id: string; target_branch_id: string
  target_legacy_simulation_run_id: string; target_checkpoint_id: string; target_branch_seed: number
  source_inventory_hash: string; normalized_clone_equivalence_hash: string; request_fingerprint: string
  idempotent_replay: boolean; created_mapping: boolean; official_branch_changed: boolean
}

export type AdminSetOfficialRunBranchRequest = {
  expected_current_official_branch_id: string | null
  command_id: string
  audit_reason: string
  explicit_confirmation: boolean
}

export type AdminSetOfficialRunBranchResponse = {
  product_run_id: string
  previous_official_branch_id: string | null
  official_branch_id: string | null
  target_branch_id: string
  changed: boolean
  idempotent_replay: boolean
  request_fingerprint: string
}

export type AdminBranchSimulationRequest = {
  expected_head_checkpoint_id: string
  command_id: string
  audit_reason: string
  explicit_confirmation: boolean
}

export type AdminBranchSimulateNextMatchRequest = AdminBranchSimulationRequest
export type AdminBranchSimulateNextRoundRequest = AdminBranchSimulationRequest
export type AdminBranchSimulateNextWeekRequest = AdminBranchSimulationRequest
export type AdminBranchSimulateNextTournamentRequest = AdminBranchSimulationRequest
export type AdminBranchSimulateFullSeasonRequest = AdminBranchSimulationRequest
export type AdminBranchSimulateWorldTourFinalsRequest = AdminBranchSimulationRequest

export type BranchSimulationMode = 'simulate_next_match' | 'simulate_next_round' | 'simulate_next_week' | 'simulate_next_tournament' | 'simulate_full_season'

export type BranchSimulationBaseSummary<Mode extends BranchSimulationMode> = {
  mode: Mode
  active_tournament: string | null
  completed_event_count: number
  next_event_index: number
}

export type BranchSimulationSummary<Mode extends BranchSimulationMode> =
  Mode extends 'simulate_full_season'
    ? BranchSimulationBaseSummary<Mode> & {
      completed_in_command_count: number
      completed_week_group_count: number
      season_complete: boolean
    }
    : BranchSimulationBaseSummary<Mode>

export type AdminBranchSimulationResponse<Mode extends BranchSimulationMode> = {
  product_run_id: string
  branch_id: string
  legacy_simulation_run_id: string
  command_id: string
  request_fingerprint: string
  idempotent_replay: boolean
  previous_head_checkpoint_id: string
  new_head_checkpoint_id: string
  previous_season: number
  previous_week: number | null
  previous_event_id: string | null
  previous_event_sequence: number | null
  current_season: number
  current_week: number | null
  current_event_id: string | null
  current_event_sequence: number | null
  official_branch_changed: boolean
  simulation_result: BranchSimulationSummary<Mode>
}

export type AdminBranchSimulateNextMatchResponse = AdminBranchSimulationResponse<'simulate_next_match'>
export type AdminBranchSimulateNextRoundResponse = AdminBranchSimulationResponse<'simulate_next_round'>
export type AdminBranchSimulateNextWeekResponse = AdminBranchSimulationResponse<'simulate_next_week'>
export type AdminBranchSimulateNextTournamentResponse = AdminBranchSimulationResponse<'simulate_next_tournament'>
export type AdminBranchSimulateFullSeasonResponse = AdminBranchSimulationResponse<'simulate_full_season'>

export type SetResult = { set_number: number; winner_player_id: string; loser_player_id: string; winner_games: number; loser_games: number; was_close_endgame: boolean; ended_by_retirement: boolean }
export type MatchResult = { match_id: string; winner_player_id: string; loser_player_id: string; player_a_id: string; player_b_id: string; best_of: number; games_to: number; win_by: number; sets: SetResult[]; sets_won: { [playerId: string]: number }; termination_reason: 'COMPLETED' | 'RETIREMENT'; retired_player_id: string | null; retired_at_set_start: number | null }
export type FinalsQualifiedPlayer = { player_id: string; race_rank: number; race_points: number; seed: number }
export type FinalsQualificationResult = { target_season: number; qualifier_count: number; reserve_count: number; qualified: FinalsQualifiedPlayer[]; reserves: FinalsQualifiedPlayer[]; ineligible_race_entries: string[] }
export type PersistedFinalsQualification = { run_id: string; season: number; source_as_of_season: number; source_as_of_week: number; qualification: FinalsQualificationResult }
export type FinalsGroupSlot = { group_id: string; slot: number; player: FinalsQualifiedPlayer }
export type FinalsGroupMatch = { match_id: string; group_id: string; match_number: number; player_a_id: string; player_b_id: string; winner_player_id: string; loser_player_id: string; match_result: MatchResult }
export type FinalsGroupStandingEntry = { group_id: string; rank: number; player_id: string; seed: number; match_wins: number; match_losses: number; set_wins: number; set_losses: number; set_differential: number; game_wins: number; game_losses: number; game_differential: number }
export type FinalsGroup = { group_id: string; slots: FinalsGroupSlot[]; matches: FinalsGroupMatch[]; standings: FinalsGroupStandingEntry[] }
export type FinalsKnockoutMatch = { stage: string; match_id: string; player_a_id: string; player_b_id: string; winner_player_id: string; loser_player_id: string; match_result: MatchResult }
export type FinalsPlacement = { player_id: string; finish: string }
export type FinalsResult = { event_id: string; season: number; qualification: FinalsQualificationResult; groups: FinalsGroup[]; knockout: FinalsKnockoutMatch[]; placements: FinalsPlacement[] }
export type PersistedFinalsResult = { run_id: string; season: number; event_id: string; source_as_of_season: number; source_as_of_week: number; result: FinalsResult }
export type FinalsSimulationResult = { run_id: string; season: number; event_id: string; qualification: PersistedFinalsQualification; result: PersistedFinalsResult; already_simulated: boolean }
export type AdminBranchSimulateWorldTourFinalsResponse = Omit<AdminBranchSimulationResponse<'simulate_next_match'>, 'simulation_result'> & { finals: FinalsSimulationResult }
export type AdminBranchExecutionResponse = AdminBranchSimulationResponse<BranchSimulationMode> | AdminBranchSimulateWorldTourFinalsResponse

export type RunStatusSummary = {
  run_id: string
  season: number
  seed: number
  progress: {
    next_event_index: number
    total_events: number
    completed_event_count: number
  }
  finals: {
    qualification_available: boolean
    result_available: boolean
  }
  rollover: {
    latest_to_season: number
    transitioned_players: number
  } | null
  source: {
    source_type: RunSourceType
    parent_run_id: string | null
  } | null
  lineage: {
    child_run_count: number
  }
  history_counts: {
    events: number
    ranking_snapshots: number
    race_snapshots: number
  }
}

export type RunWorldStatus = {
  run_id: string
  world_id: string
  source_type: 'fresh_seed' | 'rollover_bootstrap'
  stored_world_generation_fingerprint: string | null
  current_world_generation_fingerprint: string
  is_stale: boolean
  rebuild_supported: boolean
  message: string
}

export type RunTalentPlanSummary = {
  run_id: string
  season: number
  seed: number
  total_talents: number
  dataset_status: string | null
  config_version: string | null
  config_fingerprint: string | null
  countries: Array<{
    country_code: string
    planned_count: number
    quality_weights: Record<string, number>
    actual_band_counts: Record<string, number>
    bias_profile: Record<string, number>
  }>
}


export type RunProspect = {
  prospect_id: string
  run_id: string
  world_id: string
  season_start_year: number
  season_label: string
  season_week: number
  calendar_year: number
  year_week: number
  birth_year: number
  birth_year_week: number
  age: number
  country_code: string
  country_name: string | null
  status: 'prospect'
  source_type: 'weekly_15yo_cohort'
  cohort_policy_version: string
  profile_version: string
  first_name: string | null
  last_name: string | null
  display_name: string
  short_name: string | null
  identity_seed: string
  profile_seed: string
  development_seed: string
  potential_seed: string
  trait_seed: string
  profile_json: Record<string, unknown>
  development_json: Record<string, unknown>
  potential_json: Record<string, unknown>
  trait_json: Record<string, unknown>
}

export type RunProspectListResponse = {
  run_id: string
  total: number
  limit: number
  offset: number
  prospects: RunProspect[]
}


export type MaterializeRunProspectsRequest = {
  base_annual_intake_target?: number
  season_growth_rate?: number
  country_code?: string | null
  region?: string | null
  overwrite?: boolean
}

export type MaterializeRunProspectsCountryTotal = {
  country_code: string
  country_name: string | null
  materialized_count: number
}

export type MaterializeRunProspectsWeekTotal = {
  season_week: number
  materialized_count: number
}

export type MaterializeRunProspectsResponse = {
  run_id: string
  world_id: string
  season: string
  season_start_year: number
  annual_target: number
  requested_prospect_count: number
  created_count: number
  existing_count: number
  skipped_count: number
  conflict_count: number
  total_persisted_for_scope: number
  weeks_materialized: MaterializeRunProspectsWeekTotal[]
  country_totals: MaterializeRunProspectsCountryTotal[]
  already_materialized: boolean
  message: string
}

export type GeneratedPlayerProvenance = {
  run_id: string
  season: number
  player_id: string
  country_code: string
  talent_sequence: number | null
  talent_seed_value: number | null
  quality_band: string | null
  is_top_band: boolean
  source_type: 'rollover_carried' | 'planner_generated' | 'manual_override'
  override_id: string | null
  origin_source_type: 'planner_generated' | 'manual_override' | null
  origin_quality_band: string | null
  origin_override_id: string | null
  origin_season: number | null
}

export type GeneratedPlayerProvenanceListResponse = {
  run_id: string
  players: GeneratedPlayerProvenance[]
}

export type RunPlayerListItem = {
  player_id: string
  name: string
  country_code: string
  age: number
  birth_year?: number | null
  birth_year_week?: number | null
  source_type: 'rollover_carried' | 'planner_generated' | 'manual_override'
  override_id: string | null
  quality_band: string | null
  is_top_band: boolean
  origin_source_type: 'planner_generated' | 'manual_override' | null
  origin_quality_band: string | null
  origin_override_id: string | null
  origin_season: number | null
  technique: number
  movement: number
  physical: number
  mental: number
  overall: number
}

export type RunPlayersListResponse = {
  run_id: string
  total: number
  limit: number
  offset: number
  players: RunPlayerListItem[]
}

export type RunPlayerDetail = {
  player_id: string
  name: string
  country_code: string
  age: number
  birth_year?: number | null
  birth_year_week?: number | null
  play_style: string
  archetype: string
  technique: number
  movement: number
  physical: number
  mental: number
  consistency: number
  clutch: number
  recovery: number
  overall: number
  hidden_traits: {
    potential_ceiling: number
    growth_curve: string
    professionalism: number
    ambition: number
    travel_tolerance: number
    schedule_aggression: number
    injury_proneness: number
    resilience: number
  }
  source_type: 'rollover_carried' | 'planner_generated' | 'manual_override'
  quality_band: string | null
  is_top_band: boolean
  override_id: string | null
  origin_source_type: 'planner_generated' | 'manual_override' | null
  origin_quality_band: string | null
  origin_override_id: string | null
  origin_season: number | null
  talent_seed_value: number | null
  talent_sequence: number | null
}

export type PlayerCareerHistoryEntry = {
  run_id: string
  season: number
  age: number
  overall: number
  technique: number
  movement: number
  physical: number
  mental: number
  source_type: 'rollover_carried' | 'planner_generated' | 'manual_override' | null
  quality_band: string | null
  is_top_band: boolean | null
  origin_source_type: 'planner_generated' | 'manual_override' | null
  origin_quality_band: string | null
  origin_override_id: string | null
  origin_season: number | null
}

export type PlayerCareerHistoryResponse = {
  requested_run_id: string
  player_id: string
  player_name: string | null
  country_code: string | null
  entries: PlayerCareerHistoryEntry[]
}

export type PlayerCareerSeasonPerformanceEntry = {
  run_id: string
  season: number
  ranking_position: number | null
  race_position: number | null
  tournaments_played: number
  titles: number
  finals: number
  semifinals: number
  quarterfinals: number
  wins: number
  losses: number
}

export type PlayerCareerPerformanceResponse = {
  requested_run_id: string
  player_id: string
  player_name: string | null
  country_code: string | null
  entries: PlayerCareerSeasonPerformanceEntry[]
}

export type PlayerTournamentResultEntry = {
  run_id: string
  season: number
  week: number | null
  event_sequence: number
  event_id: string
  event_name: string | null
  event_category: string | null
  template_id: string | null
  finish: string | null
  is_title: boolean
  wins: number
  losses: number
  ranking_points_awarded: number | null
}

export type PlayerTournamentResultsTimelineResponse = {
  requested_run_id: string
  player_id: string
  player_name: string | null
  country_code: string | null
  entries: PlayerTournamentResultEntry[]
}

export type RunNationSummaryItem = {
  country_code: string
  country_name: string | null
  total_players: number
  average_overall: number
  average_age: number
  top_band_count: number
  manual_override_count: number
  planner_generated_count: number
  rollover_carried_count: number
  top_player_id: string | null
  top_player_name: string | null
  top_player_overall: number | null
}

export type RunNationsSummaryResponse = {
  run_id: string
  total: number
  limit: number
  offset: number
  nations: RunNationSummaryItem[]
}

export type RunNationDetail = {
  run_id: string
  country_code: string
  country_name: string | null
  total_players: number
  average_overall: number
  average_age: number
  top_band_count: number
  manual_override_count: number
  planner_generated_count: number
  rollover_carried_count: number
  average_visible_stats: {
    technique: number
    movement: number
    physical: number
    mental: number
  }
  source_mix: Record<string, number>
  band_distribution: Array<{ band: string; count: number }>
  origin_band_distribution: Array<{ band: string; count: number }>
  top_players: Array<{
    player_id: string
    name: string
    age: number
    overall: number
    source_type: 'rollover_carried' | 'planner_generated' | 'manual_override'
    quality_band: string | null
    is_top_band: boolean
  }>
}

export type RunSourceType = 'fresh_seed' | 'rollover_bootstrap'
export type LegacyRunSourceType = 'new_run' | 'bootstrap' | 'bootstrapped_rollover'
export type RunSourceTypeLike = RunSourceType | LegacyRunSourceType | (string & {})

export type RunsIndexResponse = {
  runs: Array<{
    run_id: string
    season: number
    seed: number
    progress: {
      next_event_index: number
      total_events: number
      completed_event_count: number
    }
    source_type: RunSourceType
    parent_run_id: string | null
    child_run_count: number
    world_id: string
  }>
}

export type SeasonStateResponse = {
  run: RunSummary
  season_state: {
    season: number
    next_event_index: number
    completed_event_ids: string[]
    ordered_events: Array<{
      event_id: string
      season: number
      week: number
      tour: string
      category: string
      template_id: string
    }>
  }
}

export type CanonicalSeasonState = SeasonStateResponse['season_state']
export type HistoricalBranchSeasonStateResponse = {
  product_run_id: string; branch_id: string; checkpoint_id: string; checkpoint_sequence: number; checkpoint_kind: string
  checkpoint_content_hash: string; payload_schema_version: string; checkpoint_season: number; checkpoint_week: number | null
  checkpoint_event_id: string | null; checkpoint_event_sequence: number | null; season_state: CanonicalSeasonState
}

export type CreateRunPayload = {
  run_id: string
  seed: number
  season: number
  config_version?: string
  config_fingerprint?: string
  world_id?: string | null
}

export type SimulateResponse = {
  mode: string
  run: RunSummary
  step: {
    mode: string
    season_state: SeasonStateResponse['season_state']
    tournament_result?: Record<string, unknown>
    weekly_result?: Record<string, unknown>
    season_result?: Record<string, unknown>
  }
}

export type EventRecord = {
  event_sequence: number
  event_id: string
  season: number | null
  week: number | null
  template_id: string | null
  tournament_result: Record<string, unknown> | null
}

export type EventListResponse = { run_id: string; events: EventRecord[] }

export type RunActivityItem = {
  kind:
    | 'event'
    | 'ranking_snapshot'
    | 'race_snapshot'
    | 'finals_qualification'
    | 'finals_result'
    | 'rollover'
    | 'bootstrap_child'
    | 'admin_wildcard_assignment'
    | 'admin_pre_draw_withdrawal_replacement'
    | 'admin_late_replacement_lucky_loser'
  sequence: number | null
  label: string
  season: number | null
  week: number | null
  event_id: string | null
  snapshot_sequence: number | null
  source_event_id: string | null
  related_run_id: string | null
}

export type RunActivityResponse = { run_id: string; items: RunActivityItem[] }

export type WildcardSlot = {
  slot_index: number
  entry_id: string
  assigned_player_id: string | null
}

export type WildcardStateResponse = {
  run_id: string
  event_id: string
  eligible: boolean
  eligibility_reason: string | null
  total_slots: number
  slots: WildcardSlot[]
}

export type WildcardCandidate = {
  player_id: string
  player_name: string
  country_code: string
  country_name: string | null
  source: 'main_draw_waitlist' | 'qualification_waitlist' | 'non_applicant_pool'
  source_priority: number | null
  entry_score: number | null
}

export type WildcardCandidatesResponse = {
  run_id: string
  event_id: string
  candidates: WildcardCandidate[]
}

export type WildcardActionHistoryItem = {
  action_sequence: number
  action_kind: string
  event_id: string
  assignment_payload_summary: Array<{
    slot_index: number
    player_id: string
  }>
}

export type WildcardActionHistoryResponse = {
  run_id: string
  event_id: string
  actions: WildcardActionHistoryItem[]
}

export type AssignWildcardsPayload = {
  assignments: Array<{
    slot_index: number
    player_id: string
  }>
}

export type PreDrawWithdrawablePlayer = {
  player_id: string
  player_name: string
  country_code: string
  country_name: string | null
  entry_id: string
  acceptance_status: string
}

export type PreDrawWithdrawalStateResponse = {
  run_id: string
  event_id: string
  eligible: boolean
  eligibility_reason: string | null
  withdrawable_main_draw_players: PreDrawWithdrawablePlayer[]
}

export type ApplyPreDrawWithdrawalPayload = {
  withdrawn_player_id: string
}

export type PreDrawWithdrawalResultResponse = {
  run_id: string
  event_id: string
  withdrawn_player_id: string
  replacement_player_id: string
  replacement_source: 'main_draw_waitlist' | 'qualification_waitlist'
  withdrawn_entry_id: string
  replacement_entry_id: string
  eligible: boolean
  eligibility_reason: string | null
}

export type PreDrawWithdrawalActionHistoryItem = {
  action_sequence: number
  action_kind: string
  event_id: string
  withdrawn_player_id: string
  replacement_player_id: string
  replacement_source: 'main_draw_waitlist' | 'qualification_waitlist'
  withdrawn_entry_id: string
  replacement_entry_id: string
  notes: string | null
}

export type PreDrawWithdrawalActionHistoryResponse = {
  run_id: string
  event_id: string
  actions: PreDrawWithdrawalActionHistoryItem[]
}

export type LateReplacementCandidate = {
  candidate_slot_index: number
  player_id: string
  player_name: string
  country_code: string
  country_name: string | null
  source: 'main_draw_waitlist' | 'qualification_waitlist'
  source_priority: number | null
  ranking_priority: number | null
  entry_id: string
}

export type LateReplacementCandidatesResponse = {
  run_id: string
  event_id: string
  candidates: LateReplacementCandidate[]
}

export type LateReplacementStateResponse = {
  run_id: string
  event_id: string
  eligible: boolean
  eligibility_reason: string | null
  replaceable_main_draw_players: PreDrawWithdrawablePlayer[]
  remaining_capacity: number
}

export type ApplyLateReplacementPayload = {
  withdrawn_player_id: string
}

export type LateReplacementResultResponse = {
  run_id: string
  event_id: string
  withdrawn_player_id: string
  replacement_player_id: string
  replacement_source: 'main_draw_waitlist' | 'qualification_waitlist'
  withdrawn_entry_id: string
  replacement_entry_id: string
  candidate_slot_index: number | null
  eligible: boolean
  eligibility_reason: string | null
  remaining_capacity: number
}

export type LateReplacementActionHistoryItem = {
  action_sequence: number
  action_kind: string
  event_id: string
  withdrawn_player_id: string
  replacement_player_id: string
  replacement_source: 'main_draw_waitlist' | 'qualification_waitlist'
  withdrawn_entry_id: string
  replacement_entry_id: string
  candidate_slot_index: number | null
  notes: string | null
}

export type LateReplacementActionHistoryResponse = {
  run_id: string
  event_id: string
  actions: LateReplacementActionHistoryItem[]
}

type SnapshotRecordBase = {
  snapshot_sequence: number
  snapshot_kind: string
  source_event_id: string | null
}

export type RankingSnapshot = SnapshotRecordBase & {
  payload: Record<string, unknown>
}

export type RaceSnapshot = SnapshotRecordBase & {
  payload: Record<string, unknown>
}

export type RankingSnapshotListResponse = { run_id: string; snapshots: RankingSnapshot[] }
export type RaceSnapshotListResponse = { run_id: string; snapshots: RaceSnapshot[] }

export type FinalsQualificationResponse = {
  run_id: string
  season: number
  source_as_of_season: number
  source_as_of_week: number
  qualification: Record<string, unknown>
}

export type FinalsResultResponse = {
  run_id: string
  season: number
  event_id: string
  source_as_of_season: number
  source_as_of_week: number
  result: Record<string, unknown>
}

export type FinalsSummaryResponse = {
  run_id: string
  season: number
  qualification: FinalsQualificationResponse | null
  result: FinalsResultResponse | null
}

export type FinalsSimulationResponse = {
  mode: 'simulate_world_tour_finals'
  run: RunSummary
  finals: {
    run_id: string
    season: number
    event_id: string
    qualification: FinalsQualificationResponse
    result: FinalsResultResponse
    already_simulated: boolean
  }
}

export type SeasonRolloverSummary = {
  run_id: string
  from_season: number
  to_season: number
  transitioned_players: number
  metadata: Record<string, unknown>
}

export type SeasonRolloverExecutionResponse = {
  run: RunSummary
  rollover: SeasonRolloverSummary & {
    transitions: Record<string, unknown>[]
    next_season_players: Record<string, unknown>[]
    already_persisted: boolean
  }
}

export type SeasonRolloverSummaryApiResponse = {
  rollover: SeasonRolloverSummary
}

export type NextSeasonPlayersResponse = {
  run_id: string
  to_season: number
  players: Array<{
    run_id: string
    from_season: number
    to_season: number
    player_id: string
    state: Record<string, unknown>
  }>
}

export type PlayerTransitionsResponse = {
  run_id: string
  to_season: number
  transitions: Array<{
    run_id: string
    from_season: number
    to_season: number
    player_id: string
    transition: Record<string, unknown>
  }>
}


export type BootstrapNextSeasonPayload = {
  child_run_id: string
  child_seed?: number
}

export type RunSourceSummary = {
  source_type: RunSourceTypeLike
  parent_run_id: string | null
  source_rollover_run_id: string | null
  source_rollover_from_season: number | null
  source_rollover_to_season: number | null
  world_id?: string | null
}

export type RunSourceApiResponse = {
  source: RunSourceSummary
}

export type RunLineageRecord = {
  run_id: string
  source: RunSourceSummary
  children: string[]
}

export type RunLineageApiResponse = {
  lineage: RunLineageRecord
}

export type BootstrapNextSeasonResponse = {
  run: RunSummary
  bootstrap: {
    parent_run_id: string
    child_run_id: string
    from_season: number
    to_season: number
    child_seed: number
    transitioned_players: number
    source_rollover_run_id: string
    source_rollover_to_season: number
    already_bootstrapped: boolean
  }
}

export type CountryRecord = {
  code: string
  name: string
  flag_asset: string | null
  region: string
  population: number
  area_km2?: number | null
  default_population_year?: number | null
  default_population?: number | null
  population_by_year?: Record<string, number | null> | null
  squash_popularity: number
  squash_access: number
  development_quality: number
  competition_quality: number
  elite_support: number
  squash_tradition: number
  court_count: number | null
  travel_region: string | null
  timezone_area: string | null
  notes: string | null
}

export type CountriesListResponse = {
  countries: CountryRecord[]
}

export type CountriesMetadataResponse = {
  dataset_status: string | null
  country_count: number
  source_path: string
}

export type CountryUpsertPayload = CountryRecord

export type CountriesImportPayload = {
  csv_text: string
  dry_run: boolean
}

export type CountriesImportError = {
  row_number: number | null
  field: string | null
  message: string
}

export type CountriesImportSummary = {
  total_records: number
  new_records: number
  updated_records: number
  unchanged_records: number
}

export type CountriesImportResponse = {
  ok: boolean
  dry_run: boolean
  summary: CountriesImportSummary
  errors: CountriesImportError[]
}

export type ManualPlayerAttributeOverrides = {
  technique?: number | null
  movement?: number | null
  physical?: number | null
  mental?: number | null
  consistency?: number | null
  clutch?: number | null
  recovery?: number | null
}

export type ManualPlayerHiddenTraitOverrides = {
  potential_ceiling?: number | null
  growth_curve?: string | null
  professionalism?: number | null
  ambition?: number | null
  travel_tolerance?: number | null
  schedule_aggression?: number | null
  injury_proneness?: number | null
  resilience?: number | null
}

export type ManualPlayerOverrideRecord = {
  override_id: string
  season: number
  country_code: string
  player_name: string
  player_slug?: string | null
  player_id?: string | null
  age: number
  profile_tier: 'strong' | 'elite' | 'special' | 'generational'
  quality_band_override?: string | null
  attribute_overrides?: ManualPlayerAttributeOverrides | null
  hidden_trait_overrides?: ManualPlayerHiddenTraitOverrides | null
  is_exceptional: boolean
  enabled: boolean
  notes?: string | null
}

export type ManualPlayerOverridesListResponse = {
  overrides: ManualPlayerOverrideRecord[]
}


export type ManualPlayerOverridesImportPayload = {
  csv_text: string
  dry_run: boolean
}

export type ManualPlayerOverridesImportError = {
  row_number: number | null
  field: string | null
  message: string
}

export type ManualPlayerOverridesImportSummary = {
  total_records: number
  new_records: number
  updated_records: number
  unchanged_records: number
}

export type ManualPlayerOverridesImportResponse = {
  ok: boolean
  dry_run: boolean
  summary: ManualPlayerOverridesImportSummary
  errors: ManualPlayerOverridesImportError[]
}

export type ManualPlayerOverrideUpsertPayload = ManualPlayerOverrideRecord

export type TalentClassPreviewCountry = {
  country_code: string
  country_name: string
  planned_count: number
  quality_weights: Record<string, number>
  actual_band_counts: Record<string, number>
  elite_talents: number
  tour_talents: number
  pro_depth: number
  bias_profile: Record<string, number>
  dampener: Record<string, unknown>
}

export type TalentClassYearPreviewResponse = {
  year: number
  seed: number
  dataset_status: string | null
  country_count: number
  source_path: string
  total_talents: number
  countries: TalentClassPreviewCountry[]
}

export type TalentClassSummaryCountry = {
  country_code: string
  country_name: string
  total_planned_talents: number
  average_talents_per_year: number
  total_elite_count: number
  total_special_count: number
  total_generational_count: number
  total_elite_talents: number
  total_tour_talents: number
  total_pro_depth: number
  average_elite_talents_per_year: number
  average_tour_talents_per_year: number
  average_pro_depth_per_year: number
  average_top_band_rate: number
}

export type TalentClassSummaryResponse = {
  year_start: number
  years: number
  seed: number
  dataset_status: string | null
  country_count: number
  source_path: string
  total_talents_across_span: number
  average_total_talents_per_year: number
  global_band_totals: Record<string, number>
  global_elite_talents: number
  global_tour_talents: number
  global_pro_depth: number
  countries: TalentClassSummaryCountry[]
}


export type WorldPackageStorage = {
  package_root_path: string
  world_metadata_path: string
  countries_root_path: string
  countries_index_path: string
  geography_root_path: string
  continents_path: string
  regions_path: string
  travel_regions_path: string
  timezone_areas_path: string
}

export type WorldPackage = {
  world_id: string
  name: string
  description: string
  type: 'official' | 'custom'
  status: 'active' | 'archived'
  source: 'canonical_config' | 'built_in' | 'custom_config'
  editable: boolean
  deletable: boolean
  archivable: boolean
  version: string
  fingerprint: string
  country_count: number
  continent_count: number
  region_count: number
  travel_region_count: number
  timezone_area_count: number
  used_by_run_count: number | null
  validation_status: 'valid' | 'unknown'
  storage: WorldPackageStorage
}

export type WorldPackageListResponse = {
  packages: WorldPackage[]
}

export type WorldPackageCountriesResponse = {
  world_id: string
  world_name: string
  type: 'official' | 'custom'
  source: 'canonical_config' | 'built_in' | 'custom_config'
  read_only: boolean
  country_count: number
  source_path: string
  countries: CountryRecord[]
}

export type WorldPackageContinent = { code: string, name: string }
export type WorldPackageRegion = { code: string, name: string, continent_code: string | null }
export type WorldPackageTravelRegion = { code: string, name: string, description: string | null }
export type WorldPackageTimezoneArea = { code: string, name: string, position: number }
export type WorldPackageGeography = {
  world_id: string
  continents: WorldPackageContinent[]
  regions: WorldPackageRegion[]
  travel_regions: WorldPackageTravelRegion[]
  timezone_areas: WorldPackageTimezoneArea[]
  timezone_areas_authored: boolean
}
export type WorldPackageCountryDetail = {
  package: WorldPackage
  country: CountryRecord
  region: WorldPackageRegion | null
  continent: WorldPackageContinent | null
  travel_region: WorldPackageTravelRegion | null
  timezone_area: WorldPackageTimezoneArea | null
  source_path: string
}

export type WorldPackageCountryUpdatePayload = {
  name: string
  notes: string | null
  area_km2: number | null
  region: string
  travel_region: string | null
  timezone_area: string | null
  squash_popularity: number
  squash_access: number
  development_quality: number
  competition_quality: number
  elite_support: number
  squash_tradition: number
  court_count: number | null
  expected_package_fingerprint?: string
}

export type WorldPackageCountryUpdateResponse = {
  country_detail: WorldPackageCountryDetail
  package: WorldPackage
  validation: WorldPackageValidation
}

export type WorldPackageCountryCreatePayload = Omit<WorldPackageCountryUpdatePayload, 'expected_package_fingerprint'> & {
  code: string
  population_by_year: Record<string, number>
  expected_package_fingerprint: string
}

export type WorldPackageCountryDeleteResponse = {
  deleted_country_code: string
  package: WorldPackage
  validation: WorldPackageValidation
}

export type WorldPackageCountryPopulationUpdatePayload = {
  values_by_year: Record<string, number>
  expected_package_fingerprint?: string
}



export type RunWeeklyIntakeCohortCountryAllocation = {
  country_code: string
  country_name: string | null
  allocated_count: number
  allocation_weight: number
  allocation_share: number
  effective_population: number
  population_source_type: string
  population_source_year: number | null
  is_population_estimated: boolean
}

export type RunWeeklyIntakeCohortSeasonWeek = {
  season_week: number
  target_intake_count: number
  total_allocated: number
  week_weight: number
  calendar_year: number
  year_week: number
  birth_year: number
  birth_year_week: number
  allocations: RunWeeklyIntakeCohortCountryAllocation[]
}

export type RunWeeklyIntakeCohortCountryTotal = {
  country_code: string
  country_name: string | null
  allocated_count: number
}

export type RunWeeklyIntakeCohortSeasonPreviewResponse = {
  run_id: string
  world_id: string
  world_name: string | null
  season: string
  season_start_year: number
  season_index: number
  base_annual_intake_target: number
  season_growth_rate: number
  season_variation_multiplier: number
  annual_target: number
  total_weekly_target: number
  weeks: RunWeeklyIntakeCohortSeasonWeek[]
  country_totals: RunWeeklyIntakeCohortCountryTotal[]
}

export type RunWeeklyIntakeCohortSeasonPreviewParams = {
  base_annual_intake_target?: number
  season_growth_rate?: number
  country_code?: string
  region?: string
}


export type WeeklyIntakeCountryAllocation = {
  country_code: string
  allocated_count: number
  allocation_weight: number
  allocation_share: number
  effective_population: number
  population_source_type: string
  population_source_year: number | null
  is_population_estimated: boolean
}

export type WeeklyIntakePreviewResponse = {
  world_id: string
  world_name: string | null
  season: string
  season_start_year: number
  season_week: number
  calendar_year: number
  year_week: number
  birth_year: number
  birth_year_week: number
  intake_age: number
  target_intake_count: number
  total_allocated: number
  allocations: WeeklyIntakeCountryAllocation[]
}

export type WeeklyIntakePreviewParams = {
  season: string
  season_week: number
  target_intake_count: number
  country_code?: string
  region?: string
}


export type WeeklyIntakeSeasonScheduleWeek = {
  season_week: number
  target_intake_count: number
  week_weight: number
  calendar_year: number
  year_week: number
  birth_year: number
  birth_year_week: number
}

export type WeeklyIntakeSeasonSchedulePreviewResponse = {
  world_id: string
  world_name: string | null
  season: string
  season_start_year: number
  season_index: number
  base_annual_intake_target: number
  season_growth_rate: number
  season_variation_multiplier: number
  annual_target: number
  total_weekly_target: number
  weeks: WeeklyIntakeSeasonScheduleWeek[]
}

export type WeeklyIntakeSeasonSchedulePreviewParams = {
  season: string
  base_annual_intake_target?: number
  season_growth_rate?: number
}

export type WorldPackageCountryEffectivePopulationResponse = {
  world_id: string
  world_name: string
  type: 'official' | 'custom'
  source: 'canonical_config' | 'built_in' | 'custom_config'
  read_only: boolean
  source_path: string
  country_code: string
  country_name: string
  requested_year: number
  effective_population: number
  source_year: number | null
  source_type: 'exact_population_year' | 'nearest_population_year' | 'default_population' | 'legacy_population'
  is_estimated: boolean
  default_population_year: number | null
  default_population: number | null
  legacy_population: number
  population_by_year_count: number
  usable_population_by_year_count: number
}

export type WorldPackageValidationCheck = {
  code: string
  severity: 'info' | 'warning' | 'error'
  status: 'passed' | 'warning' | 'failed'
  message: string
  path: string | null
  field: string | null
}

export type WorldPackageValidation = {
  world_id: string
  status: 'valid' | 'warnings' | 'errors'
  error_count: number
  warning_count: number
  info_count: number
  checks: WorldPackageValidationCheck[]
}


export type WorldPackageClonePayload = {
  new_world_id: string
  name: string
  description?: string | null
  dry_run: boolean
}

export type WorldPackageCloneError = {
  field: string | null
  message: string
}

export type WorldPackageCloneResponse = {
  ok: boolean
  dry_run: boolean
  source_world_id: string
  new_world_id: string
  target_path: string
  created_files: string[]
  package: WorldPackage | null
  validation: WorldPackageValidation | null
  errors: WorldPackageCloneError[]
}

export type WorldPackageImportPayload = {
  package_text: string
  dry_run: boolean
}

export type WorldPackageImportError = {
  field: string | null
  message: string
}

export type WorldPackageImportSummary = {
  total_records: number
  new_records: number
  updated_records: number
  unchanged_records: number
}

export type WorldPackageImportResponse = {
  ok: boolean
  dry_run: boolean
  countries_summary: WorldPackageImportSummary
  manual_overrides_summary: WorldPackageImportSummary
  errors: WorldPackageImportError[]
}

export type LuckyLoserRules = {
  enabled: boolean
  max_spots: number
  replacement_window: string
}

export type TournamentPointDistribution = {
  winner: number
  finalist: number
  semifinalist: number
  quarterfinalist: number
  round_of_16: number
  round_of_32: number
}

export type TournamentTemplateRecord = {
  template_id: string
  tour_level: 'WORLD_TOUR' | 'ELITE_TOUR'
  category: string
  event_name: string
  region: string
  host_country: string
  main_draw_size: number
  qualification_draw_size: number
  seeds_count: number
  qualifier_spots: number
  wild_cards: number
  byes: number
  lucky_loser_rules: LuckyLoserRules
  point_distribution_ref: string | null
  point_distribution: TournamentPointDistribution | null
  event_duration_days: number
  qualification_duration_days: number
  preferred_week_type: string | null
  seasonal_grouping: string | null
  prize_money: number
  prestige: number
  duration_in_season_weeks: number
  host_requirements: Record<string, unknown>
  category_specific_rules: Record<string, unknown>
  notes: string | null
  active: boolean
}

export type TournamentTemplatesListResponse = {
  templates: TournamentTemplateRecord[]
}

export type TournamentTemplatesMetadataResponse = {
  template_count: number
  source_path: string
  referenced_by_calendar: boolean
  referenced_template_ids: string[]
}

export type TournamentTemplatesDatasetResponse = {
  templates: TournamentTemplateRecord[]
}

export type TournamentTemplateUpsertPayload = TournamentTemplateRecord

export type TournamentTemplatesImportPayload = {
  dataset: TournamentTemplatesDatasetResponse
  dry_run: boolean
}

export type TournamentTemplatesValidationIssue = {
  field: string | null
  message: string
}

export type TournamentTemplatesImportResponse = {
  ok: boolean
  dry_run: boolean
  template_count: number
  errors: TournamentTemplatesValidationIssue[]
}

export type InitialPoolAttributes = {
  technique: number
  movement: number
  physical: number
  mental: number
  consistency: number
  clutch: number
  recovery: number
}

export type InitialPoolHiddenTraits = {
  potential_ceiling: number
  growth_curve: string
  professionalism: number
  ambition: number
  travel_tolerance: number
  schedule_aggression: number
  injury_proneness: number
  resilience: number
}

export type InitialPoolPlayer = {
  player_id: string
  name: string
  country_code: string
  nationality: string | null
  birth_year: number
  birth_year_week: number
  age_at_generation: number
  current_age_years: number
  current_ability: number
  potential_ability: number
  potential_tier: 'S' | 'A' | 'B' | 'C' | 'D'
  career_stage: string
  play_style: string
  archetype: string
  attributes: InitialPoolAttributes
  hidden_career_traits: InitialPoolHiddenTraits
  locked: boolean
  generation_source: string
  manual_override: boolean
  generation_seed: number
  generation_fingerprint: string
  created_for_season: string
}

export type InitialPoolSummary = {
  total_players: number
  locked_players: number
  unlocked_players: number
  countries_represented: number
  average_current_ability: number
  average_potential_ability: number
  by_country: Record<string, number>
  by_career_stage: Record<string, number>
  by_potential_tier: Record<string, number>
}

export type InitialPoolPopulationWeightingDiagnostic = {
  country_code: string
  allocation_weight: number
  allocation_share: number
  generated_allocation_count: number
  final_country_count: number
  effective_population_quantity: number
  legacy_population: number
  population_year_min: number
  population_year_max: number
  age_min: number
  age_max: number
  source_type_weight_shares: Record<string, number>
  estimated_weight_share: number
  source_year_min: number | null
  source_year_max: number | null
}

export type InitialPoolMetadata = {
  season: string
  seed: number
  target_pool_size: number
  country_code: string | null
  region: string | null
  dry_run: boolean
  generated_count: number
  preserved_locked_count: number
  changed_count: number
  generation_fingerprint: string
  population_weighting?: string | null
  population_year_min?: number | null
  population_year_max?: number | null
  default_population_year?: number | null
  age_min?: number | null
  age_max?: number | null
  population_weighting_diagnostics: InitialPoolPopulationWeightingDiagnostic[]
}

export type InitialPoolResponse = {
  players: InitialPoolPlayer[]
  summary: InitialPoolSummary
  metadata: InitialPoolMetadata
}

export type InitialPoolGeneratePayload = {
  season: string
  seed: number
  target_pool_size?: number
  dry_run: boolean
}

export type InitialPoolRegeneratePayload = InitialPoolGeneratePayload & {
  country_code?: string
  region?: string
}


export type CustomInitialPoolPlayerCreatePayload = Omit<InitialPoolPlayer, 'age_at_generation' | 'current_age_years' | 'locked' | 'generation_source' | 'manual_override' | 'generation_seed' | 'generation_fingerprint' | 'created_for_season'> & {
  player_id?: string
  nationality?: string | null
  created_for_season?: string
  reason?: string
}

export type InitialPoolPlayerUpdatePayload = Partial<Pick<InitialPoolPlayer, 'name' | 'nationality' | 'birth_year' | 'birth_year_week' | 'current_ability' | 'potential_ability' | 'potential_tier' | 'career_stage' | 'play_style' | 'archetype' | 'attributes' | 'hidden_career_traits'>> & {
  reason?: string
}

export type InitialPoolAuditEvent = {
  audit_id: string
  timestamp_utc: string | null
  actor: string
  action: 'create_custom_player' | 'update_player' | 'lock_player' | 'unlock_player' | 'regenerate_unlocked' | 'generate_pool'
  player_id: string | null
  season: string
  reason: string | null
  changed_fields: string[]
  before_fingerprint: string | null
  after_fingerprint: string | null
}

export type InitialPoolAuditResponse = {
  audit_events: InitialPoolAuditEvent[]
}


export type RankingTableType = 'ranking' | 'race'

export type RankingTableQueryParams = {
  table_type?: RankingTableType
  limit?: number
  country_code?: string
  search?: string
  include_zero_points?: boolean
  min_points?: number
}

export type RankingTableRow = {
  rank: number
  dense_rank: number
  ordinal_position: number
  player_id: string
  player_name: string
  country_code: string
  nationality: string
  age_years_at_season_start: number
  career_stage: string
  current_ability: number
  potential_ability: number
  potential_tier: string
  archetype: string
  play_style: string
  ranking_points: number
  race_points: number
  table_points: number
  manual_override: boolean
  source_generation: string
  locked_from_initial_pool: boolean
  movement: null
  previous_rank: null
  events_counted: null
  player_fingerprint: string | null
}

export type RankingTableSummary = {
  season: string
  table_type: RankingTableType
  player_count: number
  total_source_players: number
  ranked_player_count: number
  zero_point_players: number
  countries_represented: number
  leader_player_id: string | null
  leader_points: number | null
  generated_from_active_players_fingerprint: string
  rolling_ranking_implemented: boolean
  best_n_implemented: boolean
  movement_implemented: boolean
}

export type RankingTableMetadata = {
  season: string
  table_type: RankingTableType
  source: 'season_active_players'
  active_players_fingerprint: string
  generated_fingerprint: string
  ranking_basis: string
  filters: {
    country_code: string | null
    search: string | null
    include_zero_points: boolean
    min_points: number | null
  }
  limit: number | null
  warnings: string[]
}

export type RankingTableResponse = {
  rows: RankingTableRow[]
  summary: RankingTableSummary
  metadata: RankingTableMetadata
  validation_warnings: string[]
  validation_errors: string[]
}

export type RankingSnapshotRow = Omit<RankingTableRow, 'movement' | 'previous_rank' | 'events_counted'> & {
  previous_rank: number | null
  movement: number | null
  movement_label: 'new' | 'up' | 'down' | 'same' | 'none'
}

export type RankingSnapshotSummary = {
  season: string
  season_week: number
  table_type: RankingTableType
  player_count: number
  ranked_player_count: number
  zero_point_players: number
  countries_represented: number
  leader_player_id: string | null
  leader_points: number | null
  previous_snapshot_key: string | null
  new_entries_count: number
  moved_up_count: number
  moved_down_count: number
  unchanged_count: number
  rolling_ranking_implemented: boolean
  best_n_implemented: boolean
  movement_implemented: boolean
}

export type RankingSnapshotMetadata = {
  season: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  source: 'active_season_players'
  active_players_fingerprint: string
  point_awards_fingerprint: string | null
  ranking_table_fingerprint: string
  race_table_fingerprint: string
  snapshot_fingerprint: string
  previous_snapshot_fingerprint: string | null
  dry_run: boolean
  persisted: boolean
  generated_seed: number
  persistence_path: string | null
  publication_basis: string
  rolling_ranking_implemented: boolean
  best_n_implemented: boolean
}

export type RankingSnapshotTable = {
  table_type: RankingTableType
  rows: RankingSnapshotRow[]
  summary: RankingSnapshotSummary
  metadata: RankingSnapshotMetadata
}

export type WeeklyRankingSnapshot = {
  season: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  seed: number
  dry_run: boolean
  persisted: boolean
  ranking_table: RankingSnapshotTable
  race_table: RankingSnapshotTable
  summary: { ranking: RankingSnapshotSummary; race: RankingSnapshotSummary }
  metadata: RankingSnapshotMetadata
  validation_warnings: string[]
  validation_errors: string[]
}

export type WeeklyRankingSnapshotResult = {
  snapshot: WeeklyRankingSnapshot | null
  snapshot_exists: boolean
  summary: { ranking: RankingSnapshotSummary; race: RankingSnapshotSummary } | null
  metadata: RankingSnapshotMetadata | null
  validation_warnings: string[]
  validation_errors: string[]
}

export type WeeklyRankingSnapshotGeneratePayload = {
  seed?: number
  dry_run?: boolean
  overwrite_existing?: boolean
  include_zero_points?: boolean
  limit?: number | null
}

export type PointBreakdownTableType = 'ranking' | 'race' | 'both'

export type PlayerPointBreakdownQueryParams = {
  player_id?: string
  search?: string
  country_code?: string
  applied_only?: boolean
  table_type?: PointBreakdownTableType
  limit?: number
  include_zero_point_awards?: boolean
}

export type PlayerPointBreakdownEntry = {
  event_id: string
  season: string
  season_week: number | null
  calendar_year: number | null
  year_week: number | null
  event_name: string | null
  category: string | null
  tour_level: string | null
  template_id: string | null
  host_country: string | null
  reached_stage: string
  qualifier: boolean
  seed_number: number | null
  ranking_points_awarded: number
  race_points_awarded: number
  applied: boolean
  point_distribution_source: string | null
  source_result_fingerprint: string
  source_player_result_fingerprint: string
  award_fingerprint: string
  award_package_fingerprint: string
  result_package_fingerprint: string | null
}

export type PlayerPointBreakdownConsistency = {
  ranking_points_match_active_player: boolean
  race_points_match_active_player: boolean
  ranking_points_delta: number
  race_points_delta: number
}

export type PlayerPointBreakdown = {
  player_id: string
  player_name: string
  country_code: string
  nationality: string | null
  season: string
  current_ranking_points: number
  current_race_points: number
  breakdown_ranking_points_total: number
  breakdown_race_points_total: number
  applied_ranking_points_total: number
  applied_race_points_total: number
  unapplied_ranking_points_total: number
  unapplied_race_points_total: number
  applied_event_count: number
  total_event_count: number
  consistency: PlayerPointBreakdownConsistency
  entries: PlayerPointBreakdownEntry[]
}

export type PlayerPointBreakdownSummaryRow = {
  player_id: string
  player_name: string
  country_code: string
  ranking_points: number
  race_points: number
  breakdown_ranking_points_total: number
  breakdown_race_points_total: number
  applied_event_count: number
  total_event_count: number
  consistency_ok: boolean
  top_result_stage: string | null
  top_result_event_id: string | null
}

export type PlayerPointBreakdownMetadata = {
  season: string
  source: 'season_point_awards'
  active_players_fingerprint: string
  point_awards_fingerprint: string
  generated_fingerprint: string
  applied_only: boolean
  table_type: PointBreakdownTableType
  filters: {
    player_id: string | null
    search: string | null
    country_code: string | null
    include_zero_point_awards: boolean
  }
  limit: number | null
  rolling_ranking_implemented: boolean
  best_n_implemented: boolean
  movement_implemented: boolean
}

export type PlayerPointBreakdownResponse = {
  breakdown: PlayerPointBreakdown | null
  summary_rows: PlayerPointBreakdownSummaryRow[]
  metadata: PlayerPointBreakdownMetadata
  validation_warnings: string[]
  validation_errors: string[]
}

export type SeasonActivePlayer = {
  player_id: string
  name: string
  country_code: string
  nationality: string
  birth_year: number
  birth_year_week: number
  age_years_at_season_start: number
  age_weeks_at_season_start: number
  current_ability: number
  potential_ability: number
  potential_tier: 'S' | 'A' | 'B' | 'C' | 'D'
  career_stage: string
  play_style: string
  archetype: string
  attributes: InitialPoolAttributes
  hidden_career_traits: InitialPoolHiddenTraits
  health_status: string
  active_status: string
  ranking_points: number
  race_points: number
  protected_ranking_points: number
  season: string
  source_pool_player_id: string
  source_generation_fingerprint: string
  source_generation: 'initial_pool' | 'manual' | 'imported'
  manual_override: boolean
  locked_from_initial_pool: boolean
  bootstrap_fingerprint: string
  bootstrap_seed: number
  bootstrap_id: string
}

export type SeasonBootstrapSummary = {
  total_active_players: number
  countries_represented: number
  manual_players: number
  generated_players: number
  locked_from_initial_pool: number
  average_current_ability: number
  average_potential_ability: number
  by_potential_tier: Record<string, number>
}

export type SeasonBootstrapMetadata = {
  season: string
  source_season: string
  bootstrap_seed: number
  dry_run: boolean
  overwrite_existing: boolean
  source_initial_pool_fingerprint: string
  bootstrap_id: string
  bootstrap_fingerprint: string
  player_count: number
  persistence_path: string | null
  ranking_seeding_implemented: boolean
}

export type SeasonActivePlayersResponse = {
  players: SeasonActivePlayer[]
  summary: SeasonBootstrapSummary
  metadata: SeasonBootstrapMetadata | null
  warnings: string[]
}

export type SeasonBootstrapPayload = {
  source_season?: string
  seed: number
  dry_run: boolean
  overwrite_existing: boolean
}

export type SeasonBootstrapResponse = {
  players: SeasonActivePlayer[]
  summary: SeasonBootstrapSummary
  metadata: SeasonBootstrapMetadata
  warnings: string[]
}

export type SeasonCalendarValidationIssue = {
  severity: 'error' | 'warning' | 'info'
  code: string
  message: string
  event_id?: string | null
  field?: string | null
  context?: Record<string, unknown>
}

export type SeasonCalendarValidationSummary = {
  status: 'clean' | 'warnings' | 'errors'
  error_count: number
  warning_count: number
  info_count: number
  event_count: number
  first_season_week?: number | null
  last_season_week?: number | null
  categories: Record<string, unknown>
  tour_levels: Record<string, unknown>
  host_countries: Record<string, unknown>
}

export type SeasonCalendarValidationResponse = {
  season: string
  calendar_exists: boolean
  validation_summary: SeasonCalendarValidationSummary
  issues: SeasonCalendarValidationIssue[]
  read_only: boolean
  message: string
}

export type SeasonCalendarValidationIssueCodeMetadata = {
  code: string
  severity: 'error' | 'warning' | 'info'
  title: string
  description: string
  field?: string | null
  read_only: boolean
}

export type SeasonCalendarValidationIssueCodeRegistryResponse = {
  codes: SeasonCalendarValidationIssueCodeMetadata[]
  code_count: number
  read_only: boolean
  message: string
}

export type SeasonCalendarMetadata = {
  season: string
  season_start_calendar_year: number
  season_start_year_week: number
  total_season_weeks: number
  event_count: number
  build_seed: number | null
  build_fingerprint: string | null
  source_template_count: number
  persistence_path: string | null
  dry_run: boolean
  overwrite_existing: boolean
}

export type SeasonCalendarEvent = {
  event_id: string
  season: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  template_id: string
  event_name: string
  category: string
  tour_level: 'WORLD_TOUR' | 'ELITE_TOUR' | null
  host_country: string
  host_city: string | null
  region: string
  duration_in_season_weeks: number
  start_season_week: number | null
  end_season_week: number | null
  status: 'planned' | 'active' | 'completed' | 'cancelled' | 'scheduled'
  main_draw_size: number
  qualification_draw_size: number
  seeds_count: number
  qualifier_spots: number
  wild_cards: number
  byes: number
  point_distribution_ref: string | null
  point_distribution: Record<string, number> | null
  ranking_status: 'ranked' | 'unranked'
  ranking_points_table: Record<string, unknown>
  ranking_configuration_legacy: boolean
  required_ranking_point_stages: string[]
  missing_required_point_stages: string[]
  points_table_complete: boolean
  prize_money: number
  prestige: number
  event_level_overrides: Record<string, unknown>
  source_template_fingerprint: string | null
  template_snapshot_fingerprint: string | null
  calendar_fingerprint: string | null
  template_snapshot: Record<string, unknown>
}

export type SeasonCategoryPointsTable = {
  season: string
  category: string
  ranking_points_table: Record<string, number>
  provenance: 'seeded_from_baseline' | 'prefilled_from_previous_season' | 'manually_edited'
  source_season: string | null
}

export type SeasonCategoryPointsResponse = {
  season: string
  initialized: boolean
  categories: SeasonCategoryPointsTable[]
}

export type SeasonCalendar = {
  season: string
  events: SeasonCalendarEvent[]
  metadata: SeasonCalendarMetadata | null
  validation_warnings: SeasonCalendarValidationIssue[]
  validation_errors: SeasonCalendarValidationIssue[]
}

export type SeasonCalendarBuildSummary = {
  event_count: number
  season_weeks_used: number
  first_event_week: number | null
  last_event_week: number | null
  world_tour_events: number
  elite_tour_events: number
  validation_warning_count: number
  validation_error_count: number
  persisted: boolean
  calendar_exists: boolean
}


export type EventLifecycleStage = 'missing_calendar' | 'planned' | 'entries_generated' | 'draw_generated' | 'matches_generated' | 'in_progress' | 'completed' | 'results_extracted' | 'points_generated' | 'points_applied' | 'ranking_snapshot_published'

export type EventLifecycleNextAction = 'build_calendar' | 'generate_entries' | 'generate_draw' | 'generate_matches' | 'process_byes_or_simulate_matches' | 'extract_results' | 'generate_point_awards' | 'apply_point_awards' | 'publish_ranking_snapshot' | 'complete' | 'resolve_blocker'

export type EventArtifactStatus = {
  exists: boolean
  persisted: boolean
  fingerprint: string | null
  validation_error_count: number
  validation_warning_count: number
  summary: Record<string, unknown> | null
}

export type LifecycleMetadata = {
  season: string
  source: 'persisted_artifact_registries'
  calendar_fingerprint: string | null
  generated_fingerprint: string
  read_only: boolean
}

export type EventLifecycleStatus = {
  event_id: string
  season: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  event_name: string
  category: string
  tour_level: string | null
  host_country: string
  template_id: string
  current_stage: EventLifecycleStage
  next_recommended_action: EventLifecycleNextAction
  is_blocked: boolean
  block_reasons: string[]
  entries: EventArtifactStatus
  draw: EventArtifactStatus
  matches: EventArtifactStatus
  progression_status: Record<string, unknown> | null
  results: EventArtifactStatus
  point_awards: EventArtifactStatus
  points_applied: boolean
  ranking_snapshot: EventArtifactStatus
  validation_warnings: string[]
  validation_errors: string[]
}

export type SeasonLifecycleSummary = {
  season: string
  event_count: number
  planned_count: number
  entries_generated_count: number
  draw_generated_count: number
  matches_generated_count: number
  in_progress_count: number
  completed_count: number
  results_extracted_count: number
  points_generated_count: number
  points_applied_count: number
  ranking_snapshot_published_count: number
  blocked_count: number
}

export type SeasonLifecycleResponse = {
  season: string
  events: EventLifecycleStatus[]
  summary: SeasonLifecycleSummary
  metadata: LifecycleMetadata
  validation_warnings: string[]
  validation_errors: string[]
}

export type EventLifecycleResponse = {
  event: EventLifecycleStatus | null
  metadata: LifecycleMetadata
  validation_warnings: string[]
  validation_errors: string[]
}


export type SimulateOneEventStepName = 'preflight_lifecycle' | 'generate_entries' | 'generate_draw' | 'generate_matches' | 'process_byes' | 'simulate_draw' | 'refresh_progression' | 'extract_results' | 'generate_point_awards' | 'apply_point_awards' | 'publish_ranking_snapshot' | 'final_lifecycle'

export type SimulateOneEventStepStatusValue = 'skipped' | 'planned' | 'succeeded' | 'failed' | 'blocked'

export type SimulateOneEventDrawType = 'qualification_then_main' | 'qualification' | 'main'

export type SimulateOneEventRequest = {
  seed: number
  dry_run: boolean
  overwrite_existing: boolean
  max_steps: number
  stop_after_stage?: EventLifecycleStage | null
  apply_points: boolean
  publish_snapshot: boolean
  allow_incomplete_results?: boolean
  allow_blocked?: boolean
  include_not_entered: boolean
  max_alternates: number
  simulate_draw_type: SimulateOneEventDrawType
}

export type SimulateOneEventStepStatus = {
  step: SimulateOneEventStepName
  status: SimulateOneEventStepStatusValue
  action_detail: string
  artifact_exists_before: boolean | null
  artifact_exists_after: boolean | null
  changed_ids: string[]
  fingerprint: string | null
  warnings: string[]
  errors: string[]
  lifecycle_stage_before_step: string | null
  lifecycle_stage_after_step: string | null
  stop_reason: string | null
  service_called: string | null
  request_seed: number | null
  mutates_active_players: boolean
  mutates_ranking_snapshot: boolean
}

export type SimulateOneEventPlanSummary = {
  planned_step_count: number
  executed_step_count: number
  skipped_step_count: number
  succeeded_step_count: number
  failed_step_count: number
  blocked_step_count: number
  first_failed_step: string | null
  stop_reason: string | null
  next_safe_action: string | null
}

export type SimulateOneEventArtifactState = {
  entries_exists: boolean
  draw_exists: boolean
  matches_exists: boolean
  results_exists: boolean
  point_awards_exists: boolean
  points_applied: boolean
  ranking_snapshot_exists: boolean
}

export type SimulateOneEventChangedArtifacts = {
  entries: boolean
  draw: boolean
  matches: boolean
  results: boolean
  point_awards: boolean
  active_player_points: boolean
  ranking_snapshot: boolean
}

export type SimulateOneEventReport = {
  event_id: string
  season: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  event_name: string
  seed: number
  dry_run: boolean
  requested_apply_points: boolean
  requested_publish_snapshot: boolean
  initial_lifecycle: EventLifecycleStatus | null
  final_lifecycle: EventLifecycleStatus | null
  steps: SimulateOneEventStepStatus[]
  changed_artifacts: SimulateOneEventChangedArtifacts
  plan_summary: SimulateOneEventPlanSummary
  artifact_state_before: SimulateOneEventArtifactState
  artifact_state_after: SimulateOneEventArtifactState
  lifecycle_stage_before: string | null
  lifecycle_stage_after: string | null
  lifecycle_next_action_after: string | null
  can_continue: boolean
  safe_to_rerun: boolean
  would_duplicate_points: boolean
  would_overwrite_existing: boolean
  completed: boolean
  blocked: boolean
  validation_warnings: string[]
  validation_errors: string[]
  metadata: {
    build_fingerprint: string
    read_only: boolean
    lifecycle_preflight_fingerprint: string | null
    final_lifecycle_fingerprint: string | null
  }
}

export type SimulateOneEventResult = {
  report: SimulateOneEventReport | null
  validation_warnings: string[]
  validation_errors: string[]
}


export type SimulateSeasonWeekPreflightRequest = {
  season: string
  season_week: number
  seed: number
  apply_points: boolean
  publish_snapshot: boolean
  overwrite_existing: boolean
  include_not_entered: boolean
  max_alternates: number
  simulate_draw_type: SimulateOneEventDrawType
  max_steps_per_event: number
  stop_after_stage?: EventLifecycleStage | null
  allow_blocked: boolean
  allow_incomplete_results: boolean
  event_id_filter: string[]
  include_completed_events: boolean
}

export type SeasonWeekEventPreflight = {
  event_id: string
  event_name: string
  season: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  category: string
  tour_level: string | null
  host_country: string
  lifecycle_stage_before: string | null
  next_recommended_action_before: string | null
  one_event_report: SimulateOneEventReport
  blocked: boolean
  can_continue: boolean
  stop_reason: string | null
  planned_step_count: number
  planned_mutates_active_players: boolean
  planned_mutates_ranking_snapshot: boolean
  warnings: string[]
  errors: string[]
}

export type SeasonWeekPreflightSummary = {
  season: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  event_count: number
  planned_event_count: number
  completed_event_count: number
  blocked_event_count: number
  can_run_week: boolean
  would_apply_points: boolean
  would_publish_snapshot: boolean
  snapshot_already_exists: boolean
  week_has_multiple_events: boolean
  total_planned_steps: number
  total_planned_player_mutations: number
  total_planned_snapshot_mutations: number
  first_blocked_event_id: string | null
  stop_reason: string | null
  next_safe_action: string | null
}

export type SeasonWeekPreflightMetadata = {
  season: string
  season_week: number
  source: 'calendar_events_plus_one_event_dry_run_reports'
  calendar_fingerprint: string | null
  generated_fingerprint: string
  read_only: boolean
}

export type SimulateSeasonWeekPreflightResult = {
  season: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  events: SeasonWeekEventPreflight[]
  summary: SeasonWeekPreflightSummary
  metadata: SeasonWeekPreflightMetadata
  validation_warnings: string[]
  validation_errors: string[]
}

export type SeasonCalendarBuildPayload = {
  seed: number
  dry_run: boolean
  overwrite_existing: boolean
  season_start_calendar_year: number
  season_start_year_week: number
  include_inactive_templates: boolean
  max_events?: number | null
}

export type SeasonCalendarBuildResponse = {
  calendar: SeasonCalendar | null
  summary: SeasonCalendarBuildSummary
  metadata: SeasonCalendarMetadata | null
  validation_warnings: SeasonCalendarValidationIssue[]
  validation_errors: SeasonCalendarValidationIssue[]
}

export type EntryListValidationIssue = {
  severity: 'warning' | 'error'
  code: string
  message: string
  event_id: string | null
  player_id: string | null
  field: string | null
}

export type SeasonEventEntry = {
  entry_id: string
  player_id: string
  name: string
  country_code: string
  ranking_points: number
  race_points: number
  current_ability: number
  potential_ability: number
  entry_probability: number
  entry_score: number
  quality_score: number
  travel_score: number | null
  decision: 'accepted_main_draw' | 'accepted_qualification' | 'alternate' | 'rejected' | 'not_entered'
  acceptance_status: string
  ranking_priority: number
  seed_candidate_rank: number | null
  source_player_fingerprint: string
  bootstrap_fingerprint: string
  generated_fingerprint: string
  reason: string | null
  decision_notes: string | null
}

export type SeasonEventEntryListSummary = {
  total_active_players: number
  considered_players: number
  entered_players: number
  main_draw_acceptances: number
  qualification_acceptances: number
  alternates: number
  rejected_or_not_entered: number
  countries_represented: number
  average_entry_probability: number
  average_quality_score: number
  validation_warning_count: number
  validation_error_count: number
}

export type SeasonEventEntryListMetadata = {
  event_id: string
  season: string
  seed: number
  dry_run: boolean
  persisted: boolean
  build_fingerprint: string
  active_players_fingerprint: string
  calendar_event_fingerprint: string
  ranking_basis: string
  persistence_path: string | null
}

export type SeasonEventEntryList = {
  event_id: string
  season: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  template_id: string
  generated_from_calendar_fingerprint: string
  generated_from_active_players_fingerprint: string
  seed: number
  dry_run: boolean
  persisted: boolean
  entries: SeasonEventEntry[]
  summary: SeasonEventEntryListSummary
  metadata: SeasonEventEntryListMetadata
  validation_warnings: EntryListValidationIssue[]
  validation_errors: EntryListValidationIssue[]
}


export type DrawValidationIssue = {
  severity: 'warning' | 'error'
  code: string
  message: string
  event_id: string | null
  player_id: string | null
  field: string | null
}

export type DrawMatchRecord = {
  match_id: string
  round_number: number
  bracket_position: number
  top_slot_id: string
  bottom_slot_id: string
  top_source: string
  bottom_source: string
  winner_to_match_id: string | null
  status: 'pending' | 'bye_pending' | 'completed_placeholder'
}

export type DrawRound = {
  round_number: number
  round_name: string
  match_count: number
  matches: DrawMatchRecord[]
}

export type DrawSlotRecord = {
  slot_id: string
  bracket_position: number
  player_id: string | null
  player_name: string | null
  country_code: string | null
  entry_decision: 'accepted_main_draw' | 'accepted_qualification' | 'qualifier_placeholder' | 'bye' | 'wild_card_reserved'
  seed_number: number | null
  source_entry_id: string | null
  source_entry_fingerprint: string | null
  is_bye: boolean
  is_qualifier_placeholder: boolean
}

export type DrawSeedRecord = {
  seed_number: number
  player_id: string
  player_name: string
  ranking_priority: number
  placement_position: number
}

export type DrawByeRecord = {
  slot_id: string
  bracket_position: number
}

export type QualifierPlaceholderRecord = {
  placeholder_id: string
  slot_id: string
  bracket_position: number
  qualifier_index: number
}

export type DrawBracket = {
  draw_id: string
  draw_type: 'qualification' | 'main'
  draw_size: number
  round_count: number
  rounds: DrawRound[]
  slots: DrawSlotRecord[]
  seeds: DrawSeedRecord[]
  byes: DrawByeRecord[]
  qualifier_placeholders: QualifierPlaceholderRecord[]
  generated_fingerprint: string
}

export type DrawPackageSummary = {
  event_id: string | null
  main_draw_size: number
  qualification_draw_size: number
  main_draw_players: number
  qualification_draw_players: number
  qualifier_placeholders: number
  byes: number
  seeds: number
  validation_warning_count: number
  validation_error_count: number
}

export type DrawPackageMetadata = {
  event_id: string
  season: string
  seed: number
  dry_run: boolean
  persisted: boolean
  build_fingerprint: string
  entry_list_fingerprint: string
  calendar_event_fingerprint: string
  draw_engine_version: string | null
  persistence_path: string | null
  ranking_basis: string
}

export type SeasonEventDrawPackage = {
  event_id: string
  season: string
  template_id: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  seed: number
  dry_run: boolean
  persisted: boolean
  qualification_draw: DrawBracket | null
  main_draw: DrawBracket
  summary: DrawPackageSummary
  metadata: DrawPackageMetadata
  validation_warnings: DrawValidationIssue[]
  validation_errors: DrawValidationIssue[]
}

export type DrawGeneratePayload = {
  seed: number
  dry_run: boolean
  overwrite_existing: boolean
}

export type SeasonEventDrawPackageResult = {
  draw_package: SeasonEventDrawPackage | null
  summary: DrawPackageSummary
  metadata: DrawPackageMetadata | null
  validation_warnings: DrawValidationIssue[]
  validation_errors: DrawValidationIssue[]
  draw_package_exists: boolean
}


export type MatchValidationIssue = {
  severity: 'warning' | 'error'
  code: string
  message: string
  event_id: string | null
  match_id: string | null
  player_id: string | null
  field: string | null
}

export type MatchSimulationResult = {
  match_id: string
  winner_player_id: string
  loser_player_id: string
  scoreline: string
  games: Array<Record<string, unknown>>
  points_summary: Record<string, unknown>
  retired: boolean
  walkover: boolean
  simulation_fingerprint: string
  seed: number
}

export type MatchFormat = {
  best_of: number
  games_to: number
  win_by: number
}

export type EffectiveMatchFormatSnapshot = {
  schema_version: 'effective_match_format.v1'
  format: MatchFormat
  source_scope: 'official_default' | 'tournament_edition_override' | 'phase_override' | 'round_override'
  source_key: string
  snapshot_hash_algorithm: 'sha256'
  snapshot_hash: string
}

export type MatchInputSnapshot = {
  schema_version: 'match_input_snapshot.v1'
  match_id: string
  simulation_seed: number
  match_engine_version: string
  effective_match_format: EffectiveMatchFormatSnapshot
  context: Record<string, unknown>
  unsupported_future_inputs: Array<
    'active_gameplans' | 'rally_model_configuration' | 'rally_seed_stream'
  >
  snapshot_hash_algorithm: 'sha256'
  snapshot_hash: string
}

export type SeasonMatchRecord = {
  match_id: string
  event_id: string
  draw_type: 'qualification' | 'main'
  round_number: number
  round_name: string
  bracket_position: number
  top_slot_id: string
  bottom_slot_id: string
  top_source: string
  bottom_source: string
  top_player_id: string | null
  bottom_player_id: string | null
  top_player_name: string | null
  bottom_player_name: string | null
  top_country_code: string | null
  bottom_country_code: string | null
  status: 'pending' | 'blocked_waiting_for_sources' | 'bye_auto_advance_pending' | 'completed' | 'walkover_placeholder'
  winner_player_id: string | null
  loser_player_id: string | null
  scoreline: string | null
  simulated_result: MatchSimulationResult | null
  winner_to_match_id: string | null
  effective_match_format: EffectiveMatchFormatSnapshot
  match_input_snapshot: MatchInputSnapshot | null
  source_draw_fingerprint: string
  generated_fingerprint: string
  result_fingerprint: string | null
  simulation_seed: number | null
  result_notes: string | null
}

export type MatchPackageSummary = {
  event_id: string | null
  total_matches: number
  qualification_matches: number
  main_draw_matches: number
  pending_matches: number
  completed_matches: number
  blocked_matches: number
  bye_auto_advances: number
  validation_warning_count: number
  validation_error_count: number
}

export type MatchPackageMetadata = {
  event_id: string
  season: string
  seed: number
  dry_run: boolean
  persisted: boolean
  build_fingerprint: string
  draw_package_fingerprint: string
  active_players_fingerprint: string
  match_engine_version: string | null
  persistence_path: string | null
  ranking_updates_implemented: boolean
  qualification_winners_promoted: boolean
}

export type SeasonEventMatchPackage = {
  event_id: string
  season: string
  template_id: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  seed: number
  dry_run: boolean
  persisted: boolean
  qualification_matches: SeasonMatchRecord[]
  main_draw_matches: SeasonMatchRecord[]
  summary: MatchPackageSummary
  metadata: MatchPackageMetadata
  validation_warnings: MatchValidationIssue[]
  validation_errors: MatchValidationIssue[]
}

export type MatchGeneratePayload = {
  seed: number
  dry_run: boolean
  overwrite_existing: boolean
  tournament_edition_match_format?: MatchFormat | null
  phase_match_formats?: Record<string, MatchFormat>
  round_match_formats?: Record<string, MatchFormat>
}

export type MatchSimulatePayload = {
  seed: number
}

export type TournamentProgressionStatus = {
  event_id: string
  season: string
  qualification_status: 'not_started' | 'in_progress' | 'completed' | 'not_applicable'
  main_draw_status: 'not_started' | 'in_progress' | 'completed' | 'not_applicable'
  event_status: 'not_started' | 'in_progress' | 'completed' | 'blocked'
  qualification_winners_ready: boolean
  qualification_winners_promoted: boolean
  pending_matches: number
  blocked_matches: number
  completed_matches: number
  bye_auto_advances_pending: number
  champion_player_id: string | null
  champion_name: string | null
  finalist_player_id: string | null
  finalist_name: string | null
  warnings: MatchValidationIssue[]
  errors: MatchValidationIssue[]
}

export type ProgressionCommandPayload = {
  seed: number
}

export type SimulateRoundPayload = {
  seed: number
  draw_type: 'qualification' | 'main'
  round_number: number
}

export type SimulateDrawPayload = {
  seed: number
  draw_type: 'qualification' | 'main'
}

export type ProgressionCommandResult = {
  event_id: string
  action: 'process_byes' | 'refresh_status' | 'simulate_round' | 'simulate_draw' | 'promote_qualifiers' | 'advance_completed'
  match_package: SeasonEventMatchPackage
  progression_status: TournamentProgressionStatus
  changed_match_ids: string[]
  promoted_player_ids: string[]
  validation_warnings: MatchValidationIssue[]
  validation_errors: MatchValidationIssue[]
  metadata: Record<string, unknown>
}

export type SeasonEventMatchPackageResult = {
  match_package: SeasonEventMatchPackage | null
  summary: MatchPackageSummary
  metadata: MatchPackageMetadata | null
  validation_warnings: MatchValidationIssue[]
  validation_errors: MatchValidationIssue[]
  match_package_exists: boolean
}



export type EventResultValidationIssue = MatchValidationIssue

export type PlayerResultSummary = {
  player_id: string
  player_name: string | null
  country_code: string | null
  seed_number: number | null
  entry_decision: string | null
  qualifier: boolean
  wildcard: boolean
  ranking_priority: number | null
}

export type PlayerEventResult = {
  player_id: string
  player_name: string | null
  country_code: string | null
  draw_type: 'qualification' | 'main' | 'both'
  entry_decision: string | null
  seed_number: number | null
  qualifier: boolean
  reached_stage: 'champion' | 'finalist' | 'semifinal' | 'quarterfinal' | 'round_of_16' | 'round_of_32' | 'round_of_64' | 'round_of_128' | 'qualification_winner' | 'qualification_final' | 'qualification_semifinal' | 'qualification_round' | 'main_draw_participant' | 'unknown'
  final_round_number: number | null
  eliminated_by_player_id: string | null
  eliminated_by_player_name: string | null
  last_match_id: string | null
  wins: number
  losses: number
  walkovers_received: number
  byes_received: number
  retired_or_walkover_loss: boolean
  points_awarded: number
  race_points_awarded: number
  prize_money_awarded: number
}

export type MatchResultRef = {
  match_id: string
  draw_type: 'qualification' | 'main'
  round_number: number
  round_name: string
  bracket_position: number
  winner_player_id: string | null
  loser_player_id: string | null
  scoreline: string | null
  result_fingerprint: string | null
}

export type EventResultSummary = {
  event_id: string
  completion_status: 'incomplete' | 'complete' | 'blocked'
  player_count: number
  main_draw_player_count: number
  qualification_player_count: number
  completed_matches: number
  incomplete_matches: number
  champion_player_id: string | null
  finalist_player_id: string | null
  qualification_winner_count: number
  ranking_points_awarded_total: number
  race_points_awarded_total: number
  validation_warning_count: number
  validation_error_count: number
}

export type EventResultMetadata = {
  event_id: string
  season: string
  seed: number
  dry_run: boolean
  persisted: boolean
  build_fingerprint: string
  match_package_fingerprint: string | null
  draw_package_fingerprint: string | null
  calendar_event_fingerprint: string | null
  ranking_updates_implemented: boolean
  points_awarding_implemented: boolean
  persistence_path: string | null
}

export type SeasonEventResultPackage = {
  event_id: string
  season: string
  template_id: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  event_name: string | null
  category: string | null
  tour_level: string | null
  host_country: string | null
  seed: number
  dry_run: boolean
  persisted: boolean
  completion_status: 'incomplete' | 'complete' | 'blocked'
  champion: PlayerResultSummary | null
  finalist: PlayerResultSummary | null
  semifinalists: PlayerResultSummary[]
  quarterfinalists: PlayerResultSummary[]
  qualification_winners: PlayerResultSummary[]
  player_results: PlayerEventResult[]
  match_result_refs: MatchResultRef[]
  summary: EventResultSummary
  metadata: EventResultMetadata
  validation_warnings: EventResultValidationIssue[]
  validation_errors: EventResultValidationIssue[]
}

export type EventResultExtractPayload = {
  seed: number
  dry_run: boolean
  overwrite_existing: boolean
}

export type SeasonEventResultPackageResult = {
  result_package: SeasonEventResultPackage | null
  summary: EventResultSummary | null
  metadata: EventResultMetadata | null
  validation_warnings: EventResultValidationIssue[]
  validation_errors: EventResultValidationIssue[]
  result_package_exists: boolean
}

export type EntryListGeneratePayload = {
  seed: number
  dry_run: boolean
  overwrite_existing: boolean
  max_alternates: number
  include_not_entered: boolean
}

export type SeasonEventEntryListResult = {
  entry_list: SeasonEventEntryList | null
  summary: SeasonEventEntryListSummary
  metadata: SeasonEventEntryListMetadata | null
  validation_warnings: EntryListValidationIssue[]
  validation_errors: EntryListValidationIssue[]
  entry_list_exists: boolean
}

export type PointAwardValidationIssue = MatchValidationIssue

export type PlayerPointAward = {
  player_id: string
  player_name: string | null
  country_code: string | null
  reached_stage: PlayerEventResult['reached_stage']
  qualifier: boolean
  seed_number: number | null
  ranking_points_awarded: number
  race_points_awarded: number
  previous_ranking_points: number | null
  previous_race_points: number | null
  projected_ranking_points: number | null
  projected_race_points: number | null
  source_result_fingerprint: string
  source_player_result_fingerprint: string
  award_fingerprint: string
}

export type PointAwardSummary = {
  event_id: string
  player_count: number
  awarded_player_count: number
  total_ranking_points: number
  total_race_points: number
  champion_player_id: string | null
  champion_points: number
  finalist_player_id: string | null
  finalist_points: number
  applied: boolean
  validation_warning_count: number
  validation_error_count: number
}

export type PointAwardMetadata = {
  event_id: string
  season: string
  seed: number
  dry_run: boolean
  persisted: boolean
  applied: boolean
  build_fingerprint: string
  result_package_fingerprint: string
  point_distribution_fingerprint: string
  point_distribution_source: string
  ranking_updates_implemented: boolean
  rolling_ranking_implemented: boolean
  best_n_implemented: boolean
  persistence_path: string | null
}

export type EventPointAwardPackage = {
  event_id: string
  season: string
  template_id: string
  event_name: string | null
  category: string | null
  tour_level: string | null
  seed: number
  dry_run: boolean
  persisted: boolean
  applied: boolean
  awards: PlayerPointAward[]
  summary: PointAwardSummary
  metadata: PointAwardMetadata
  validation_warnings: PointAwardValidationIssue[]
  validation_errors: PointAwardValidationIssue[]
}

export type PointAwardGeneratePayload = {
  seed: number
  dry_run: boolean
  overwrite_existing: boolean
}

export type PointAwardApplyPayload = {
  seed: number
  allow_reapply: boolean
}

export type EventPointAwardPackageResult = {
  award_package: EventPointAwardPackage | null
  summary: PointAwardSummary | null
  metadata: PointAwardMetadata | null
  validation_warnings: PointAwardValidationIssue[]
  validation_errors: PointAwardValidationIssue[]
  award_package_exists: boolean
  applied: boolean
}

export type UpdatedPlayerPoints = {
  player_id: string
  player_name: string | null
  previous_ranking_points: number
  previous_race_points: number
  new_ranking_points: number
  new_race_points: number
  delta_ranking_points: number
  delta_race_points: number
}

export type PointAwardApplyResult = {
  event_id: string
  applied: boolean
  award_package: EventPointAwardPackage | null
  updated_players: UpdatedPlayerPoints[]
  validation_warnings: PointAwardValidationIssue[]
  validation_errors: PointAwardValidationIssue[]
  metadata: PointAwardMetadata | null
}


export type SeasonWeekRecoveryRequest = {
  season: string
  season_week: number
  event_id_filter: string[]
  include_completed_events: boolean
}

export type SeasonWeekRecoveryRerunFlags = {
  overwrite_existing: boolean
  apply_points: boolean
  publish_snapshot: boolean
  allow_blocked: boolean
  allow_incomplete_results: boolean
}

export type SeasonWeekRecoveryEventAction = 'generate_entries' | 'generate_draw' | 'generate_matches' | 'simulate_matches' | 'extract_results' | 'generate_point_awards' | 'apply_point_awards' | 'publish_week_snapshot' | 'rerun_event_safe' | 'resolve_blocker' | 'complete'

export type SeasonWeekRecoveryEvent = {
  event_id: string
  event_name: string
  season: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  category: string
  tour_level: string | null
  host_country: string
  current_stage: string
  next_recommended_action: string
  is_blocked: boolean
  block_reasons: string[]
  entries_exists: boolean
  draw_exists: boolean
  matches_exists: boolean
  results_exists: boolean
  point_awards_exists: boolean
  points_applied: boolean
  ranking_snapshot_exists: boolean
  safe_to_rerun_event: boolean
  duplicate_points_risk: boolean
  overwrite_risk: boolean
  needs_manual_attention: boolean
  recommended_event_action: SeasonWeekRecoveryEventAction
  recommended_rerun_flags: SeasonWeekRecoveryRerunFlags
  warnings: string[]
  errors: string[]
}

export type SeasonWeekRecoverySummary = {
  season: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  event_count: number
  completed_event_count: number
  partial_event_count: number
  blocked_event_count: number
  points_generated_count: number
  points_applied_count: number
  snapshot_exists: boolean
  week_complete: boolean
  week_partial: boolean
  week_blocked: boolean
  ready_for_point_application: boolean
  ready_for_snapshot_publication: boolean
  duplicate_points_risk_count: number
  overwrite_risk_count: number
  manual_attention_count: number
  next_safe_action: 'resolve_blockers' | 'rerun_week_without_overwrite' | 'rerun_week_with_apply_points' | 'publish_week_snapshot' | 'review_completed_week' | 'build_calendar' | 'no_events' | null
  recommended_week_rerun_flags: SeasonWeekRecoveryRerunFlags
  rollback_available: boolean
}

export type SeasonWeekRecoveryMetadata = {
  season: string
  season_week: number
  source: 'persisted_artifact_recovery_read_model'
  generated_fingerprint: string
  read_only: boolean
}

export type SeasonWeekRecoveryResult = {
  season: string
  season_week: number
  events: SeasonWeekRecoveryEvent[]
  summary: SeasonWeekRecoverySummary
  metadata: SeasonWeekRecoveryMetadata
  validation_warnings: string[]
  validation_errors: string[]
}

export type SeasonReadinessRequest = {
  season: string
  include_empty_weeks: boolean
  include_completed_weeks: boolean
  event_id_filter: string[]
}

export type SeasonWeekReadinessStatus = 'empty' | 'planned' | 'partial' | 'blocked' | 'ready_for_point_application' | 'ready_for_snapshot_publication' | 'complete'
export type SeasonReadinessNextSafeAction = 'build_calendar' | 'run_week' | 'recover_week' | 'apply_points' | 'publish_snapshot' | 'resolve_blockers' | 'review_completed_season' | 'no_events'

export type SeasonWeekReadinessRow = {
  season: string
  season_week: number
  calendar_year: number
  year_week: number
  event_count: number
  has_events: boolean
  status: SeasonWeekReadinessStatus
  week_complete: boolean
  week_partial: boolean
  week_blocked: boolean
  ready_for_point_application: boolean
  ready_for_snapshot_publication: boolean
  snapshot_exists: boolean
  completed_event_count: number
  partial_event_count: number
  blocked_event_count: number
  points_generated_count: number
  points_applied_count: number
  duplicate_points_risk_count: number
  overwrite_risk_count: number
  manual_attention_count: number
  next_safe_action: SeasonReadinessNextSafeAction
  recommended_week_rerun_flags: SeasonWeekRecoveryRerunFlags
  representative_event_ids: string[]
  warnings: string[]
  errors: string[]
  recovery_fingerprint: string | null
}

export type SeasonReadinessSummary = {
  season: string
  total_weeks: number
  weeks_with_events: number
  empty_weeks: number
  complete_weeks: number
  partial_weeks: number
  blocked_weeks: number
  ready_for_point_application_weeks: number
  ready_for_snapshot_publication_weeks: number
  weeks_missing_snapshot_after_points: number
  total_events: number
  total_blocked_events: number
  total_manual_attention_count: number
  first_incomplete_week: number | null
  first_blocked_week: number | null
  next_week_to_run: number | null
  season_ready_to_continue: boolean
  season_complete: boolean
  next_safe_action: SeasonReadinessNextSafeAction
}

export type SeasonReadinessMetadata = {
  season: string
  source: 'season_week_recovery_aggregation'
  generated_fingerprint: string
  read_only: boolean
}

export type SeasonReadinessResult = {
  season: string
  weeks: SeasonWeekReadinessRow[]
  summary: SeasonReadinessSummary
  metadata: SeasonReadinessMetadata
  validation_warnings: string[]
  validation_errors: string[]
}


export type SeasonRangePreflightRequest = {
  season: string
  start_week: number
  end_week: number
  include_empty_weeks: boolean
  include_completed_weeks: boolean
  event_id_filter: string[]
  apply_points: boolean
  publish_snapshot: boolean
  stop_on_blocked: boolean
}

export type SeasonRangeAction = 'skip_empty' | 'skip_complete' | 'run_week' | 'apply_points' | 'publish_snapshot' | 'blocked' | 'recover_week'
export type SeasonRangeNextSafeAction = 'run_range' | 'resolve_blockers' | 'apply_points' | 'publish_snapshots' | 'recover_week' | 'nothing_to_run' | 'adjust_range' | 'build_calendar'

export type SeasonRangePreflightWeek = {
  season: string
  season_week: number
  calendar_year: number
  year_week: number
  status: SeasonWeekReadinessStatus
  event_count: number
  has_events: boolean
  week_complete: boolean
  week_blocked: boolean
  week_partial: boolean
  ready_for_point_application: boolean
  ready_for_snapshot_publication: boolean
  snapshot_exists: boolean
  next_safe_action: SeasonReadinessNextSafeAction
  recommended_week_rerun_flags: SeasonWeekRecoveryRerunFlags
  range_action: SeasonRangeAction
  would_mutate_if_executed: boolean
  would_apply_points_if_executed: boolean
  would_publish_snapshot_if_executed: boolean
  warnings: string[]
  errors: string[]
}

export type SeasonRangePreflightSummary = {
  season: string
  start_week: number
  end_week: number
  total_weeks_in_range: number
  empty_weeks: number
  completed_weeks: number
  runnable_weeks: number
  point_application_weeks: number
  snapshot_publication_weeks: number
  blocked_weeks: number
  recoverable_weeks: number
  skipped_weeks: number
  first_unsafe_week: number | null
  first_blocked_week: number | null
  first_runnable_week: number | null
  range_safe_to_run: boolean
  would_apply_points: boolean
  would_publish_snapshots: boolean
  next_safe_action: SeasonRangeNextSafeAction
  recommended_run_flags: SeasonWeekRecoveryRerunFlags
  mutation_warning: string
}

export type SeasonRangePreflightMetadata = {
  season: string
  source: 'season_readiness_range_preflight'
  season_readiness_fingerprint: string | null
  generated_fingerprint: string
  read_only: boolean
}

export type SeasonRangePreflightResult = {
  season: string
  start_week: number
  end_week: number
  weeks: SeasonRangePreflightWeek[]
  summary: SeasonRangePreflightSummary
  metadata: SeasonRangePreflightMetadata
  validation_warnings: string[]
  validation_errors: string[]
}


export type RunSeasonRangeRequest = SeasonRangePreflightRequest & {
  seed: number
  overwrite_existing: boolean
  allow_unsafe_run: boolean
  allow_blocked: boolean
  allow_incomplete_results: boolean
  include_not_entered: boolean
  max_alternates: number
  max_steps_per_event: number
  simulate_draw_type: SimulateOneEventDrawType
  stop_after_week: number | null
  max_weeks_to_run: number | null
}

export type SeasonRangeRunNextSafeAction = 'inspect_range_preflight' | 'resolve_blockers' | 'inspect_recovery' | 'rerun_range' | 'inspect_season_readiness' | 'review_completed_range'

export type SeasonRangeRunWeekResult = {
  season_week: number
  calendar_year: number
  year_week: number
  status_before: string
  range_action: string
  run_order: number | null
  skipped: boolean
  skip_reason: string | null
  week_run_result: RunSeasonWeekResult | null
  succeeded: boolean
  blocked: boolean
  failed: boolean
  warnings: string[]
  errors: string[]
}

export type SeasonRangeRunSummary = {
  season: string
  start_week: number
  end_week: number
  attempted_week_count: number
  skipped_empty_week_count: number
  skipped_complete_week_count: number
  executed_week_count: number
  succeeded_week_count: number
  blocked_week_count: number
  failed_week_count: number
  point_application_week_count: number
  snapshot_publication_week_count: number
  run_started: boolean
  run_completed: boolean
  stopped_early: boolean
  first_failed_week: number | null
  first_blocked_week: number | null
  stop_reason: string | null
  next_safe_action: SeasonRangeRunNextSafeAction
  no_rollback_warning: string
  range_safe_to_run_preflight: boolean
}

export type SeasonRangeRunMetadata = {
  season: string
  source: 'range_preflight_plus_week_execution_reports'
  range_preflight_fingerprint: string
  final_fingerprint: string
  read_only: boolean
}

export type RunSeasonRangeResult = {
  preflight: SeasonRangePreflightResult
  weeks: SeasonRangeRunWeekResult[]
  summary: SeasonRangeRunSummary
  metadata: SeasonRangeRunMetadata
  validation_warnings: string[]
  validation_errors: string[]
}

export type RunSeasonWeekRequest = SimulateSeasonWeekPreflightRequest & {
  allow_unsafe_run: boolean
}

export type SeasonWeekRunEventResult = {
  event_id: string
  event_name: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  run_order: number
  preflight_stop_reason: string | null
  initial_stage: string | null
  final_stage: string | null
  event_report: SimulateOneEventReport
  succeeded: boolean
  blocked: boolean
  changed_artifacts: SimulateOneEventChangedArtifacts
  warnings: string[]
  errors: string[]
}

export type SeasonWeekRunSummary = {
  season: string
  season_week: number
  calendar_year: number | null
  year_week: number | null
  event_count: number
  attempted_event_count: number
  succeeded_event_count: number
  blocked_event_count: number
  failed_event_count: number
  points_applied_event_count: number
  snapshot_published: boolean
  snapshot_skipped: boolean
  snapshot_already_existed: boolean
  can_run_preflight: boolean
  run_started: boolean
  run_completed: boolean
  stopped_early: boolean
  first_failed_event_id: string | null
  stop_reason: string | null
  next_safe_action: string | null
}

export type SeasonWeekRunMetadata = {
  season: string
  season_week: number
  source: 'week_preflight_plus_one_event_execution_reports'
  preflight_fingerprint: string
  final_fingerprint: string
  read_only: boolean
}

export type RunSeasonWeekResult = {
  preflight: SimulateSeasonWeekPreflightResult
  events: SeasonWeekRunEventResult[]
  summary: SeasonWeekRunSummary
  metadata: SeasonWeekRunMetadata
  validation_warnings: string[]
  validation_errors: string[]
}


export type SeasonTemplateSlotValidationPreview = {
  template_id?: string | null
  template_exists?: boolean | null
  status?: 'clean' | 'warnings' | 'errors' | null
  error_count?: number
  warning_count?: number
  issue_count?: number
  issue_codes?: string[]
  error_codes?: string[]
  warning_codes?: string[]
  read_only?: boolean
}



export type SeasonTemplateSlotConflictPreview = {
  template_id?: string | null
  template_exists?: boolean | null
  status?: 'clean' | 'warnings' | 'info' | null
  warning_count?: number
  info_count?: number
  conflict_count?: number
  conflict_codes?: string[]
  warning_codes?: string[]
  info_codes?: string[]
  busiest_week?: number | null
  busiest_week_slot_count?: number | null
  read_only?: boolean
}

export type SeasonBuilderPreflightRequest = {
  target_season_label: string
  source_type: string
  source_template_id?: string | null
  overwrite_policy?: string | null
  requested_by?: string | null
}

export type SeasonBuilderPreflightResponse = {
  can_build: boolean
  target_season_label: string
  source_type: string
  source_template_id: string | null
  preflight_fingerprint: string
  reviewed_diff_id: string
  target_calendar_exists: boolean | null
  target_event_count: number | null
  source_resolved: boolean
  source_summary: Record<string, unknown>
  authoritative_diff_summary: Record<string, unknown>
  template_slot_validation_preview?: SeasonTemplateSlotValidationPreview | null
  template_slot_conflict_preview?: SeasonTemplateSlotConflictPreview | null
  template_conflict_diagnostics_overview?: SeasonTemplateConflictDiagnosticsOverview | null
  validation_warnings: string[]
  validation_errors: string[]
  audit_preview: Record<string, unknown>
}


export type DryRunTemplateConflictSummaryPreview = {
  available?: boolean
  read_only?: boolean
  non_blocking?: boolean
  status?: 'clean' | 'warnings' | 'info' | null
  warning_count?: number
  info_count?: number
  conflict_count?: number
  conflict_codes?: string[]
  busiest_week?: number | null
  busiest_week_slot_count?: number | null
  source?: string
  message?: string
}

export type CandidateIdentitySummary = {
  candidate_count?: number
  candidate_ids?: string[]
  candidate_identity_keys?: string[]
  duplicate_candidate_ids?: string[]
  duplicate_candidate_identity_keys?: string[]
  read_only?: boolean
  mutation_permitted?: boolean
  message?: string
}

export type CandidateIdentityOverview = {
  available?: boolean
  candidate_count?: number
  safe_for_future_reference?: boolean
  has_duplicate_candidate_ids?: boolean
  has_duplicate_candidate_identity_keys?: boolean
  identity_source?: string
  id_strategy?: string
  key_strategy?: string
  read_only?: boolean
  mutation_permitted?: boolean
  message?: string
}

export type CandidateIdentityContract = {
  identity_source?: string
  id_strategy?: string
  key_strategy?: string
  key_components?: string[]
  candidate_count?: number
  has_duplicate_candidate_ids?: boolean
  has_duplicate_candidate_identity_keys?: boolean
  safe_for_future_reference?: boolean
  read_only?: boolean
  mutation_permitted?: boolean
  message?: string
}

export type CandidateIdentityFingerprint = {
  fingerprint?: string
  fingerprint_algorithm?: string
  fingerprint_payload_version?: number
  candidate_count?: number
  candidate_ids?: string[]
  candidate_identity_keys?: string[]
  safe_for_future_reference?: boolean
  target_season_label?: string | null
  source_type?: string | null
  source_template_id?: string | null
  read_only?: boolean
  mutation_permitted?: boolean
  message?: string
}

export type CandidateIdentityReviewReference = {
  reference_type?: string
  reference_id?: string
  fingerprint_algorithm?: string
  fingerprint_payload_version?: number
  candidate_count?: number
  safe_for_future_reference?: boolean
  can_reference_future_apply?: boolean
  read_only?: boolean
  mutation_permitted?: boolean
  message?: string
}

export type FutureApplyReferenceContract = {
  available?: boolean | null
  contract_type?: string | null
  candidate_identity_reference_type?: string | null
  candidate_identity_reference_id?: string | null
  candidate_identity_fingerprint?: string | null
  candidate_identity_set_referenceable?: boolean | null
  main_future_command_reference_ready?: boolean | null
  apply_execution_enabled?: boolean | null
  create_only_apply_required?: boolean | null
  read_only?: boolean | null
  mutation_permitted?: boolean | null
  message?: string | null
}

export type FutureApplyRequestValidationPreview = {
  available?: boolean | null
  validation_type?: string | null
  requested_candidate_identity_reference_id?: string | null
  requested_candidate_identity_fingerprint?: string | null
  requested_candidate_identity_reference_type?: string | null
  expected_candidate_identity_reference_id?: string | null
  expected_candidate_identity_fingerprint?: string | null
  expected_candidate_identity_reference_type?: string | null
  reference_id_matches?: boolean | null
  fingerprint_matches?: boolean | null
  reference_type_matches?: boolean | null
  contract_referenceable?: boolean | null
  apply_execution_enabled?: boolean | null
  read_only?: boolean | null
  mutation_permitted?: boolean | null
  message?: string | null
}

export type CreateOnlyApplyExecutionPreflightPreview = {
  available?: boolean | null
  preflight_type?: string | null
  target_absent?: boolean | null
  create_only_scope_confirmed?: boolean | null
  audit_metadata_present?: boolean | null
  future_apply_reference_contract_available?: boolean | null
  future_apply_request_validation_available?: boolean | null
  candidate_identity_reference_matches?: boolean | null
  main_future_command_reference_ready?: boolean | null
  all_known_preconditions_met?: boolean | null
  execution_enabled?: boolean | null
  can_execute?: boolean | null
  read_only?: boolean | null
  mutation_permitted?: boolean | null
  message?: string | null
}

export type CreateOnlyApplyAuditMetadataPreview = {
  available?: boolean | null
  preview_type?: string | null
  requested_by_present?: boolean | null
  audit_reason_present?: boolean | null
  explicit_confirmation_present?: boolean | null
  explicit_confirmation_matches?: boolean | null
  mutation_scope_present?: boolean | null
  mutation_scope_matches?: boolean | null
  required_confirmation_phrase?: string | null
  required_mutation_scope?: string | null
  all_required_audit_metadata_present?: boolean | null
  execution_enabled?: boolean | null
  can_execute?: boolean | null
  read_only?: boolean | null
  mutation_permitted?: boolean | null
  message?: string | null
}

export type DisabledExecutionContractSummary = {
  available?: boolean | null
  summary_type?: string | null
  future_apply_reference_contract_available?: boolean | null
  future_apply_request_validation_available?: boolean | null
  audit_metadata_available?: boolean | null
  execution_preflight_available?: boolean | null
  identity_reference_matches?: boolean | null
  audit_metadata_complete?: boolean | null
  all_known_preconditions_met?: boolean | null
  all_preview_layers_available?: boolean | null
  execution_enabled?: boolean | null
  can_execute?: boolean | null
  read_only?: boolean | null
  mutation_permitted?: boolean | null
  message?: string | null
}


export type GuardedApplyExecutionGateSpecification = {
  available?: boolean | null
  specification_type?: string | null
  final_checklist_available?: boolean | null
  final_readiness_checks_passed?: boolean | null
  requires_target_absent?: boolean | null
  requires_create_only_scope?: boolean | null
  requires_allowed_source_type?: string | null
  requires_allowed_overwrite_policy?: string | null
  requires_audit_metadata?: boolean | null
  required_confirmation_phrase?: string | null
  required_mutation_scope?: string | null
  requires_identity_reference_match?: boolean | null
  requires_summary_execution_disabled?: boolean | null
  requires_endpoint_disabled_before_execution?: boolean | null
  gate_specification_complete?: boolean | null
  execution_enabled?: boolean | null
  can_execute?: boolean | null
  read_only?: boolean | null
  mutation_permitted?: boolean | null
  message?: string | null
}

export type FinalGuardedApplyReadinessChecklist = {
  available?: boolean | null
  checklist_type?: string | null
  endpoint_disabled?: boolean | null
  endpoint_execution_disabled?: boolean | null
  endpoint_mutation_disabled?: boolean | null
  summary_available?: boolean | null
  summary_all_preview_layers_available?: boolean | null
  summary_all_known_preconditions_met?: boolean | null
  summary_execution_disabled?: boolean | null
  summary_mutation_disabled?: boolean | null
  all_readiness_checks_passed?: boolean | null
  execution_enabled?: boolean | null
  can_execute?: boolean | null
  read_only?: boolean | null
  mutation_permitted?: boolean | null
  message?: string | null
}

export type FutureApplyExecutionDecisionSummary = {
  available?: boolean | null
  summary_type?: string | null
  boundary_contract_available?: boolean | null
  execution_boundary_intact?: boolean | null
  preview_stack_only?: boolean | null
  manual_validation_only?: boolean | null
  separate_execution_phase_required?: boolean | null
  operator_review_required?: boolean | null
  future_execution_phase_may_be_considered?: boolean | null
  execution_authorized?: boolean | null
  execution_enabled?: boolean | null
  can_execute?: boolean | null
  read_only?: boolean | null
  mutation_permitted?: boolean | null
  message?: string | null
}

export type FutureApplyExecutionBoundaryContract = {
  available?: boolean | null
  contract_type?: string | null
  gate_specification_available?: boolean | null
  gate_specification_complete?: boolean | null
  actual_execution_endpoint_exists?: boolean | null
  actual_execution_wiring_enabled?: boolean | null
  mutation_path_enabled?: boolean | null
  preview_stack_only?: boolean | null
  execution_boundary_intact?: boolean | null
  requires_separate_execution_phase?: boolean | null
  requires_separate_endpoint_wiring?: boolean | null
  requires_separate_mutation_audit?: boolean | null
  execution_enabled?: boolean | null
  can_execute?: boolean | null
  read_only?: boolean | null
  mutation_permitted?: boolean | null
  message?: string | null
}

export type SeasonBuilderFutureApplyRequestValidationPreviewRequest = {
  target_season_label: string
  source_type: string
  source_template_id?: string | null
  overwrite_policy?: string | null
  preflight_fingerprint?: string | null
  reviewed_diff_id?: string | null
  requested_candidate_identity_reference_id?: string | null
  requested_candidate_identity_fingerprint?: string | null
  requested_candidate_identity_reference_type?: string | null
  requested_by?: string | null
  audit_reason?: string | null
  explicit_confirmation?: string | null
  mutation_scope?: string | null
}

export type SeasonBuilderFutureApplyRequestValidationPreviewResponse = {
  enabled: boolean
  can_execute: boolean
  can_mutate: boolean
  target_season_label: string
  source_type: string
  source_template_id?: string | null
  overwrite_policy?: string | null
  future_apply_reference_contract?: FutureApplyReferenceContract | null
  future_apply_request_validation_preview?: FutureApplyRequestValidationPreview | null
  create_only_apply_execution_preflight_preview?: CreateOnlyApplyExecutionPreflightPreview | null
  create_only_apply_audit_metadata_preview?: CreateOnlyApplyAuditMetadataPreview | null
  disabled_execution_contract_summary?: DisabledExecutionContractSummary | null
  final_guarded_apply_readiness_checklist?: FinalGuardedApplyReadinessChecklist | null
  guarded_apply_execution_gate_specification?: GuardedApplyExecutionGateSpecification | null
  future_apply_execution_boundary_contract?: FutureApplyExecutionBoundaryContract | null
  future_apply_execution_decision_summary?: FutureApplyExecutionDecisionSummary | null
  audit_preview?: Record<string, unknown> | null
}

export type CandidateIdentityReadinessOverview = {
  available?: boolean
  candidate_identity_fingerprint?: string | null
  candidate_identity_reference_id?: string | null
  candidate_identity_reference_type?: string | null
  can_reference_candidate_identity_set?: boolean
  candidate_reference_status?: string
  main_future_command_reference_ready?: boolean
  read_only?: boolean
  mutation_permitted?: boolean
  message?: string
}

export type DryRunIdentityReadiness = {
  status?: string
  items?: Array<{
    area?: string
    status?: string
    message?: string
  }>
  future_command_reference?: Record<string, unknown>
  candidate_identity_readiness_overview?: CandidateIdentityReadinessOverview | null
}

export type SeasonBuilderDryRunBuildRequest = {
  target_season_label: string
  source_type: string
  source_template_id?: string | null
  overwrite_policy?: string | null
  preflight_fingerprint: string
  reviewed_diff_id: string
  requested_by?: string | null
  audit_reason?: string | null
  explicit_confirmation?: string | null
  mutation_scope?: string | null
}

export type SeasonBuilderDryRunBuildResponse = {
  command: string
  enabled: boolean
  can_execute: boolean
  can_mutate: boolean
  target_season_label: string
  source_type: string
  source_template_id: string | null
  overwrite_policy: string | null
  preflight_fingerprint: string
  reviewed_diff_id: string
  template_slot_validation_preview?: SeasonTemplateSlotValidationPreview | null
  template_slot_conflict_preview?: SeasonTemplateSlotConflictPreview | null
  template_conflict_diagnostics_overview?: SeasonTemplateConflictDiagnosticsOverview | null
  validation_errors: string[]
  validation_warnings: string[]
  audit_preview: Record<string, unknown>
  generation_design_preview: Record<string, unknown>
  candidate_event_contract_preview: Record<string, unknown>
  conflict_contract_preview: Record<string, unknown>
  dry_run_result_contract_preview: Record<string, unknown>
  dry_run_result_preview: Record<string, unknown> & {
    identity_readiness?: DryRunIdentityReadiness | null
    template_conflict_summary?: DryRunTemplateConflictSummaryPreview | null
    candidate_identity_summary?: CandidateIdentitySummary | null
    candidate_identity_contract?: CandidateIdentityContract | null
    candidate_identity_overview?: CandidateIdentityOverview | null
    candidate_identity_fingerprint?: CandidateIdentityFingerprint | null
    candidate_identity_review_reference?: CandidateIdentityReviewReference | null
    future_apply_reference_contract?: FutureApplyReferenceContract | null
  }
  message: string
}

export type SeasonBuilderApplyCommandContractRequest = {
  target_season_label: string
  source_type: string
  source_template_id?: string | null
  overwrite_policy?: string | null
  preflight_fingerprint: string
  reviewed_diff_id: string
  dry_run_result_fingerprint: string
  dry_run_result_id: string
  requested_by?: string | null
  audit_reason?: string | null
  explicit_confirmation?: string | null
  mutation_scope?: string | null
}

export type SeasonBuilderApplyCommandContractResponse = {
  command: string
  enabled: boolean
  can_execute: boolean
  can_mutate: boolean
  target_season_label: string
  source_type: string
  source_template_id: string | null
  overwrite_policy: string | null
  validation_errors: string[]
  validation_warnings: string[]
  audit_preview: Record<string, unknown>
  audit_trail_contract_preview: Record<string, unknown>
  safety_gate_contract_preview: Record<string, unknown>
  required_identity: Record<string, unknown>
  required_audit_metadata: Record<string, unknown>
  message: string
}


export type SeasonBuilderApplyCreateOnlyCommandRequest = {
  target_season_label: string
  source_type: string
  source_template_id?: string | null
  overwrite_policy?: string | null
  preflight_fingerprint: string
  reviewed_diff_id: string
  dry_run_result_fingerprint: string
  dry_run_result_id: string
  requested_candidate_identity_reference_id: string
  requested_candidate_identity_fingerprint: string
  requested_candidate_identity_reference_type: string
  requested_by: string
  audit_reason: string
  explicit_confirmation: string
  mutation_scope: string
}

export type SeasonBuilderApplyCreateOnlyCommandResponse = {
  command: string
  enabled: boolean
  can_execute: boolean
  can_mutate: boolean
  applied: boolean
  target_season_label: string
  validation_errors: string[]
  validation_warnings: string[]
  created_calendar_summary: Record<string, unknown>
  created_event_preview: Array<Record<string, unknown>>
  created_calendar_identity: Record<string, unknown>
  created_calendar_validation_preview: Record<string, unknown>
  apply_gate_summary: Record<string, unknown>
  applied_event_count: number
  dry_run_identity: Record<string, unknown>
  audit_preview: Record<string, unknown>
  audit_record_id?: string | null
  audit_persisted?: boolean
  audit_persistence_status?: string
  audit_record_fingerprint?: string | null
  audit_storage_summary?: Record<string, unknown>
  message: string
}
export type SeasonBuilderApplyCreateOnlyReadinessResponse = {
  command: string
  enabled: boolean
  can_execute_apply: boolean
  can_mutate: boolean
  would_create_calendar: boolean
  service_insert_applicable: boolean
  target_season_label: string
  validation_errors: string[]
  validation_warnings: string[]
  apply_gate_summary: Record<string, unknown>
  dry_run_identity: Record<string, unknown>
  candidate_summary: Record<string, unknown>
  audit_preview: Record<string, unknown>
  message: string
}

export type DryRunValidationSummary = {
  status: 'clean' | 'warnings' | 'blocking'
  blocking_count: number
  warning_count: number
  info_count: number
  blocking_reasons: string[]
  warning_reasons: string[]
  info_messages: string[]
  candidate_status_counts: {
    planned: number
    replacement: number
    conflict: number
    invalid: number
  }
  conflict_type_counts: {
    week_conflicts: number
    slot_conflicts: number
    policy_conflicts: number
    validation_conflicts: number
  }
}


export type ViewerOfficialRunContext = {
  product_run_id: string
  product_run_display_name: string
  product_run_status: string
  product_run_storage_kind: string
  product_run_read_only: boolean
  official_branch_id: string
  official_branch_display_name: string
  official_branch_status: string
  official_branch_read_only: boolean
  official_branch_seed: number | null
  legacy_simulation_run_id: string
  head_checkpoint_id: string
  head_checkpoint_kind: string
  current_season: number | null
  current_week: number | null
  current_event_id: string | null
  current_event_sequence: number | null
  resolution_version: string
}
