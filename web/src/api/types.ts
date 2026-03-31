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

export type RankingSnapshot = {
  snapshot_sequence: number
  snapshot_kind: string
  source_event_id: string | null
  payload: Record<string, unknown>
}

export type RankingSnapshotListResponse = { run_id: string; snapshots: RankingSnapshot[] }
export type RaceSnapshotListResponse = RankingSnapshotListResponse

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
  source_type: string
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
