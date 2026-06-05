import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  makeEventListResponse,
  makeFinalsSummary,
  makeRaceSnapshotListResponse,
  makeRankingSnapshotListResponse,
  makeRunStatusSummary,
  makeSeasonStateResponse,
} from '../../../test/viewerDeferredFixtures'
import { renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { ViewerTourDeferredPage } from './ViewerTourDeferredPage'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(),
  getRun: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listEvents: vi.fn(),
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn(),
}))

vi.mock('../../../api/client', () => api)

function renderTourDeferredPage(): void {
  renderWithViewerProviders(<ViewerTourDeferredPage kind="matches" />, {
    activeRunId: 'run alpha',
  })
}

describe('ViewerTourDeferredPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.getRun.mockResolvedValue(
      makeSeasonStateResponse({
        run: {
          next_event_index: 1,
          total_events: 7,
          completed_event_ids: ['British Open 2034'],
        },
        season_state: {
          next_event_index: 1,
          completed_event_ids: ['British Open 2034'],
          ordered_events: [
            {
              event_id: 'British Open 2034',
              season: 2034,
              week: 20,
              tour: 'World Tour',
              category: 'Platinum',
              template_id: 'BO',
            },
            {
              event_id: 'Egyptian Open 2034',
              season: 2034,
              week: 21,
              tour: 'World Tour',
              category: 'Gold',
              template_id: 'EO',
            },
          ],
        },
      }),
    )
    api.getRunStatusSummary.mockResolvedValue(
      makeRunStatusSummary({
        progress: {
          next_event_index: 1,
          total_events: 7,
          completed_event_count: 5,
        },
        finals: { qualification_available: true, result_available: false },
        history_counts: { events: 5, ranking_snapshots: 2, race_snapshots: 1 },
      }),
    )
    api.listEvents.mockResolvedValue(
      makeEventListResponse({
        events: [
          {
            event_sequence: 1,
            event_id: 'British Open 2034',
            season: 2034,
            week: 20,
            template_id: 'BO',
            tournament_result: {},
          },
        ],
      }),
    )
    api.listRankingSnapshots.mockResolvedValue(
      makeRankingSnapshotListResponse({
        snapshots: [
          {
            snapshot_sequence: 3,
            snapshot_kind: 'ranking',
            source_event_id: 'British Open 2034',
            payload: {},
          },
        ],
      }),
    )
    api.listRaceSnapshots.mockResolvedValue(
      makeRaceSnapshotListResponse({
        snapshots: [
          {
            snapshot_sequence: 4,
            snapshot_kind: 'race',
            source_event_id: 'British Open 2034',
            payload: {},
          },
        ],
      }),
    )
    api.getFinalsSummary.mockResolvedValue(
      makeFinalsSummary({
        qualification: {
          run_id: 'run alpha',
          season: 2034,
          source_as_of_season: 2034,
          source_as_of_week: 61,
          qualification: {},
        },
      }),
    )
  })

  it('preserves Tour metadata label order and source link order', async () => {
    renderTourDeferredPage()

    await waitFor(() =>
      expect(screen.getByText('Egyptian Open 2034')).toBeInTheDocument(),
    )

    expect(screen.getAllByRole('term').map((term) => term.textContent)).toEqual(
      [
        'Active run ID',
        'Season',
        'Completed/persisted event count',
        'Ordered calendar event count',
        'Ranking snapshot count',
        'Race snapshot count',
        'Finals availability',
        'Next scheduled event',
        'Latest persisted event',
        'Latest ranking snapshot',
        'Latest race snapshot',
      ],
    )
    expect(screen.getAllByRole('link').map((link) => link.textContent)).toEqual(
      [
        'Finals qualification available',
        'Egyptian Open 2034',
        'British Open 2034',
        '#3',
        '#4',
        'Open active run calendar',
        'Open active run tournaments',
        'Open active run rankings',
        'Open active run race',
        'Open run browser',
      ],
    )
    expect(
      screen.getByRole('link', { name: 'Open active run calendar' }),
    ).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar')
    expect(
      screen.getByRole('link', { name: 'Open active run tournaments' }),
    ).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments')
    expect(
      screen.getByRole('link', { name: 'Open active run rankings' }),
    ).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings')
    expect(
      screen.getByRole('link', { name: 'Open active run race' }),
    ).toHaveAttribute('href', '/viewer/runs/run%20alpha/race')
    expect(
      screen.getByRole('link', { name: 'Open run browser' }),
    ).toHaveAttribute('href', '/viewer/runs')
  })
})
