import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  EventListResponse,
  FinalsSummaryResponse,
  RankingSnapshotListResponse,
  RaceSnapshotListResponse,
  RunStatusSummary,
  SeasonStateResponse,
} from '../../../api/types'
import { useViewerDeferredSourceQueries } from './useViewerDeferredSourceQueries'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(),
  getRun: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listEvents: vi.fn(),
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn(),
}))

vi.mock('../../../api/client', () => api)

type HookProps = Parameters<typeof useViewerDeferredSourceQueries>[0]

function statusSummary(
  overrides: Partial<RunStatusSummary> = {},
): RunStatusSummary {
  return {
    run_id: 'run alpha',
    season: 2034,
    seed: 1001,
    progress: {
      next_event_index: 0,
      total_events: 61,
      completed_event_count: 5,
    },
    finals: {
      qualification_available: false,
      result_available: false,
    },
    rollover: null,
    source: null,
    lineage: {
      child_run_count: 0,
    },
    history_counts: {
      events: 3,
      ranking_snapshots: 2,
      race_snapshots: 1,
    },
    ...overrides,
  }
}

function eventsResponse(count: number): EventListResponse {
  return {
    run_id: 'run alpha',
    events: Array.from({ length: count }, (_, index) => ({
      event_sequence: index + 1,
      event_id: `event-${index + 1}`,
      season: 2034,
      week: index + 1,
      template_id: `template-${index + 1}`,
      tournament_result: {},
    })),
  }
}

function rankingSnapshotsResponse(count = 1): RankingSnapshotListResponse {
  return {
    run_id: 'run alpha',
    snapshots: Array.from({ length: count }, (_, index) => ({
      snapshot_sequence: index + 1,
      snapshot_kind: 'ranking',
      source_event_id: `event-${index + 1}`,
      payload: {},
    })),
  }
}

function raceSnapshotsResponse(count = 1): RaceSnapshotListResponse {
  return {
    run_id: 'run alpha',
    snapshots: Array.from({ length: count }, (_, index) => ({
      snapshot_sequence: index + 1,
      snapshot_kind: 'race',
      source_event_id: `event-${index + 1}`,
      payload: {},
    })),
  }
}

function finalsSummary(): FinalsSummaryResponse {
  return {
    run_id: 'run alpha',
    season: 2034,
    qualification: null,
    result: null,
  }
}

function seasonState(orderedEventCount: number): SeasonStateResponse {
  return {
    run: {
      run_id: 'run alpha',
      season: 2034,
      seed: 1001,
      config_version: null,
      config_fingerprint: null,
      next_event_index: 0,
      total_events: 99,
      completed_event_ids: [],
    },
    season_state: {
      season: 2034,
      next_event_index: 0,
      completed_event_ids: [],
      ordered_events: Array.from({ length: orderedEventCount }, (_, index) => ({
        event_id: `ordered-${index + 1}`,
        season: 2034,
        week: index + 1,
        tour: 'World Tour',
        category: 'Gold',
        template_id: `ordered-template-${index + 1}`,
      })),
    },
  }
}

function setupApiMocks(): void {
  api.getRun.mockResolvedValue(seasonState(7))
  api.getRunStatusSummary.mockResolvedValue(statusSummary())
  api.listEvents.mockResolvedValue(eventsResponse(2))
  api.listRankingSnapshots.mockResolvedValue(rankingSnapshotsResponse())
  api.listRaceSnapshots.mockResolvedValue(raceSnapshotsResponse())
  api.getFinalsSummary.mockResolvedValue(finalsSummary())
}

function renderHookProbe(props: HookProps): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  function Probe(): JSX.Element {
    const result = useViewerDeferredSourceQueries(props)
    return (
      <dl>
        <dt>loading</dt>
        <dd>{String(result.isLoadingMetadata)}</dd>
        <dt>error</dt>
        <dd>{String(result.hasMetadataError)}</dd>
        <dt>has metadata</dt>
        <dd>{String(result.hasAnySourceMetadata)}</dd>
        <dt>event count</dt>
        <dd>{String(result.metadata.eventCount)}</dd>
        <dt>ordered count</dt>
        <dd>{String(result.orderedEventCount)}</dd>
      </dl>
    )
  }

  render(
    <QueryClientProvider client={client}>
      <Probe />
    </QueryClientProvider>,
  )
}

describe('useViewerDeferredSourceQueries', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupApiMocks()
  })

  it('disables all API calls when no active run is selected', () => {
    renderHookProbe({
      activeRunId: null,
      kind: 'match-odds',
      scope: 'prediction',
    })

    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.getRunStatusSummary).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expect(api.getFinalsSummary).not.toHaveBeenCalled()
    expect(screen.getByText('loading').nextSibling).toHaveTextContent('false')
    expect(screen.getByText('error').nextSibling).toHaveTextContent('false')
    expect(screen.getByText('has metadata').nextSibling).toHaveTextContent('false')
  })

  it('defaults to status/events/ranking/race/finals calls without loading the run', async () => {
    renderHookProbe({
      activeRunId: 'run alpha',
      kind: 'match-odds',
      scope: 'prediction',
    })

    await waitFor(() => expect(api.getRunStatusSummary).toHaveBeenCalledWith('run alpha'))
    expect(api.listEvents).toHaveBeenCalledWith('run alpha')
    expect(api.listRankingSnapshots).toHaveBeenCalledWith('run alpha')
    expect(api.listRaceSnapshots).toHaveBeenCalledWith('run alpha')
    expect(api.getFinalsSummary).toHaveBeenCalledWith('run alpha')
    expect(api.getRun).not.toHaveBeenCalled()
  })

  it('loads the active run only when includeRun is true', async () => {
    renderHookProbe({
      activeRunId: 'run alpha',
      kind: 'match-odds',
      scope: 'prediction',
      includeRun: true,
    })

    await waitFor(() => expect(api.getRun).toHaveBeenCalledWith('run alpha'))
  })

  it('skips finals calls when includeFinals is false while preserving other source calls', async () => {
    renderHookProbe({
      activeRunId: 'run alpha',
      kind: 'match-odds',
      scope: 'prediction',
      includeFinals: false,
    })

    await waitFor(() => expect(api.getRunStatusSummary).toHaveBeenCalledWith('run alpha'))
    expect(api.listEvents).toHaveBeenCalledWith('run alpha')
    expect(api.listRankingSnapshots).toHaveBeenCalledWith('run alpha')
    expect(api.listRaceSnapshots).toHaveBeenCalledWith('run alpha')
    expect(api.getFinalsSummary).not.toHaveBeenCalled()
  })

  it('preserves status-progress event count fallback order', async () => {
    renderHookProbe({
      activeRunId: 'run alpha',
      kind: 'draws',
      scope: 'tour',
      eventCountMode: 'status-progress',
    })

    await waitFor(() => expect(screen.getByText('event count').nextSibling).toHaveTextContent('2'))

    vi.clearAllMocks()
    setupApiMocks()
    api.listEvents.mockImplementationOnce(() => new Promise(() => undefined))
    renderHookProbe({
      activeRunId: 'run alpha',
      kind: 'draws',
      scope: 'tour-progress-fallback',
      eventCountMode: 'status-progress',
    })

    await waitFor(() => expect(screen.getAllByText('event count')[1].nextSibling).toHaveTextContent('5'))

    vi.clearAllMocks()
    setupApiMocks()
    api.listEvents.mockImplementationOnce(() => new Promise(() => undefined))
    api.getRunStatusSummary.mockResolvedValueOnce(
      statusSummary({
        progress: {
          next_event_index: 0,
          total_events: 61,
          completed_event_count: undefined as unknown as number,
        },
        history_counts: {
          events: 9,
          ranking_snapshots: 2,
          race_snapshots: 1,
        },
      }),
    )
    renderHookProbe({
      activeRunId: 'run alpha',
      kind: 'draws',
      scope: 'tour-history-fallback',
      eventCountMode: 'status-progress',
    })

    await waitFor(() => expect(screen.getAllByText('event count')[2].nextSibling).toHaveTextContent('9'))
  })

  it('preserves run-ordered event count behavior', async () => {
    renderHookProbe({
      activeRunId: 'run alpha',
      kind: 'title-leaders',
      scope: 'stats',
      includeRun: true,
      eventCountMode: 'run-ordered',
    })

    await waitFor(() => expect(screen.getByText('event count').nextSibling).toHaveTextContent('7'))
  })
})
