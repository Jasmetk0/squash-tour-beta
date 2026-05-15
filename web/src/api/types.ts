export type HealthResponse = { status: 'ok' }

export type RunSummary = {
  run_id: string
  season: number
  seed: number
  config_version: string | null
  config_fingerprint: string | null
  next_event_index: number
  total_events: number
  completed_event_ids: string[]
}

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

export type CreateRunPayload = {
  run_id: string
  seed: number
  season: number
  config_version?: string
  config_fingerprint?: string
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
  wealth_support: number
  squash_popularity: number
  squash_tradition: number
  system_quality: number
  competition_density: number
  federation_quality: number
  court_count: number | null
  travel_region: string | null
  notes: string | null
  style_dna: Record<string, number>
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
  countries: TalentClassSummaryCountry[]
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
  severity: 'warning' | 'error'
  code: string
  message: string
  event_id: string | null
  field: string | null
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
  prize_money: number
  prestige: number
  event_level_overrides: Record<string, unknown>
  source_template_fingerprint: string | null
  template_snapshot_fingerprint: string | null
  calendar_fingerprint: string | null
  template_snapshot: Record<string, unknown>
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
}

export type MatchSimulatePayload = {
  seed: number
}

export type SeasonEventMatchPackageResult = {
  match_package: SeasonEventMatchPackage | null
  summary: MatchPackageSummary
  metadata: MatchPackageMetadata | null
  validation_warnings: MatchValidationIssue[]
  validation_errors: MatchValidationIssue[]
  match_package_exists: boolean
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
