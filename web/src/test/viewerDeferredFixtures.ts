import type {
  EventListResponse,
  FinalsSummaryResponse,
  RaceSnapshotListResponse,
  RankingSnapshotListResponse,
  RunNationDetail,
  RunNationSummaryItem,
  RunPlayerListItem,
  RunStatusSummary,
  SeasonStateResponse,
} from '../api/types'

export const defaultViewerRunId = 'run alpha'
export const defaultViewerSeason = 2034
export const defaultViewerSeed = 1001

type DeepPartial<T> = {
  [K in keyof T]?: T[K] extends Array<infer U>
    ? Array<DeepPartial<U>>
    : T[K] extends object | null
      ? DeepPartial<NonNullable<T[K]>> | T[K]
      : T[K]
}

export function makeRunStatusSummary(
  overrides: DeepPartial<RunStatusSummary> = {},
): RunStatusSummary {
  return {
    run_id: defaultViewerRunId,
    season: defaultViewerSeason,
    seed: defaultViewerSeed,
    progress: {
      next_event_index: 0,
      total_events: 61,
      completed_event_count: 5,
      ...overrides.progress,
    },
    finals: {
      qualification_available: false,
      result_available: false,
      ...overrides.finals,
    },
    rollover: null,
    source: null,
    lineage: {
      child_run_count: 0,
      ...overrides.lineage,
    },
    history_counts: {
      events: 3,
      ranking_snapshots: 2,
      race_snapshots: 1,
      ...overrides.history_counts,
    },
    ...overrides,
  } as RunStatusSummary
}

export function makeEventListResponse(
  countOrOverrides: number | Partial<EventListResponse> = 1,
): EventListResponse {
  if (typeof countOrOverrides !== 'number') {
    return {
      run_id: defaultViewerRunId,
      events: [],
      ...countOrOverrides,
    }
  }

  return {
    run_id: defaultViewerRunId,
    events: Array.from({ length: countOrOverrides }, (_, index) => ({
      event_sequence: index + 1,
      event_id: `event-${index + 1}`,
      season: defaultViewerSeason,
      week: index + 1,
      template_id: `template-${index + 1}`,
      tournament_result: {},
    })),
  }
}

export function makeRankingSnapshotListResponse(
  countOrOverrides: number | Partial<RankingSnapshotListResponse> = 1,
): RankingSnapshotListResponse {
  if (typeof countOrOverrides !== 'number') {
    return {
      run_id: defaultViewerRunId,
      snapshots: [],
      ...countOrOverrides,
    }
  }

  return {
    run_id: defaultViewerRunId,
    snapshots: Array.from({ length: countOrOverrides }, (_, index) => ({
      snapshot_sequence: index + 1,
      snapshot_kind: 'ranking',
      source_event_id: `event-${index + 1}`,
      payload: {},
    })),
  }
}

export function makeRaceSnapshotListResponse(
  countOrOverrides: number | Partial<RaceSnapshotListResponse> = 1,
): RaceSnapshotListResponse {
  if (typeof countOrOverrides !== 'number') {
    return {
      run_id: defaultViewerRunId,
      snapshots: [],
      ...countOrOverrides,
    }
  }

  return {
    run_id: defaultViewerRunId,
    snapshots: Array.from({ length: countOrOverrides }, (_, index) => ({
      snapshot_sequence: index + 1,
      snapshot_kind: 'race',
      source_event_id: `event-${index + 1}`,
      payload: {},
    })),
  }
}

export function makeFinalsSummary(
  overrides: Partial<FinalsSummaryResponse> = {},
): FinalsSummaryResponse {
  return {
    run_id: defaultViewerRunId,
    season: defaultViewerSeason,
    qualification: null,
    result: null,
    ...overrides,
  }
}

export function makeSeasonStateResponse(
  orderedEventCountOrOverrides: number | DeepPartial<SeasonStateResponse> = 0,
): SeasonStateResponse {
  const overrides =
    typeof orderedEventCountOrOverrides === 'number'
      ? {}
      : orderedEventCountOrOverrides
  const orderedEventCount =
    typeof orderedEventCountOrOverrides === 'number'
      ? orderedEventCountOrOverrides
      : 0

  return {
    run: {
      run_id: defaultViewerRunId,
      season: defaultViewerSeason,
      seed: defaultViewerSeed,
      config_version: null,
      config_fingerprint: null,
      next_event_index: 0,
      total_events: 99,
      completed_event_ids: [],
      ...overrides.run,
    },
    season_state: {
      season: defaultViewerSeason,
      next_event_index: 0,
      completed_event_ids: [],
      ordered_events: Array.from({ length: orderedEventCount }, (_, index) => ({
        event_id: `ordered-${index + 1}`,
        season: defaultViewerSeason,
        week: index + 1,
        tour: 'World Tour',
        category: 'Gold',
        template_id: `ordered-template-${index + 1}`,
      })),
      ...overrides.season_state,
    },
  } as SeasonStateResponse
}

export function makeRunPlayer(
  overrides: Partial<RunPlayerListItem> = {},
): RunPlayerListItem {
  return {
    player_id: 'player-1',
    name: 'Player One',
    country_code: 'EGY',
    age: 24,
    source_type: 'planner_generated',
    override_id: null,
    quality_band: 'elite',
    is_top_band: true,
    origin_source_type: 'planner_generated',
    origin_quality_band: 'elite',
    origin_override_id: null,
    origin_season: defaultViewerSeason,
    technique: 90,
    movement: 88,
    physical: 87,
    mental: 86,
    overall: 88,
    ...overrides,
  }
}

export function makeRunNation(
  overrides: Partial<RunNationSummaryItem & RunNationDetail> = {},
): RunNationSummaryItem {
  return {
    country_code: 'EGY',
    country_name: 'Egypt',
    total_players: 1,
    average_overall: 88,
    average_age: 24,
    top_band_count: 1,
    manual_override_count: 0,
    planner_generated_count: 1,
    rollover_carried_count: 0,
    top_player_id: 'player-1',
    top_player_name: 'Player One',
    top_player_overall: 88,
    ...overrides,
  }
}
