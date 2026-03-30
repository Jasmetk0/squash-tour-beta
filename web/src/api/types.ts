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
