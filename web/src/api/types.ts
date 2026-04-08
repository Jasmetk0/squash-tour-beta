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
