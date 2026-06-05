import { screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  makeEventListResponse,
  makeFinalsSummary,
  makeRaceSnapshotListResponse,
  makeRankingSnapshotListResponse,
  makeRunStatusSummary,
  makeSeasonStateResponse,
} from '../../../test/viewerDeferredFixtures'
import {
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
} from '../../../test/viewerTestUtils'
import { ViewerRankingDeferredPage } from './ViewerRankingDeferredPage'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(),
  getRun: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listEvents: vi.fn(),
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn(),
}))

vi.mock('../../../api/client', () => api)

function renderRankingDeferredPage(): void {
  renderWithViewerProviders(<ViewerRankingDeferredPage kind="elo" />, {
    activeRunId: 'run alpha',
  })
}

describe('ViewerRankingDeferredPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.getRun.mockResolvedValue(makeSeasonStateResponse(0))
    api.getRunStatusSummary.mockResolvedValue(
      makeRunStatusSummary({
        history_counts: { events: 5, ranking_snapshots: 1, race_snapshots: 1 },
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
            snapshot_sequence: 12,
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
            snapshot_sequence: 8,
            snapshot_kind: 'race',
            source_event_id: 'British Open 2034',
            payload: {},
          },
        ],
      }),
    )
    api.getFinalsSummary.mockResolvedValue(makeFinalsSummary())
  })

  it('preserves ranking nullish ordered-event fallback and encoded source links', async () => {
    renderRankingDeferredPage()

    expect(
      screen.getByRole('heading', { level: 2, name: 'Elo Ranking' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Available source metadata' }),
    ).toBeInTheDocument()

    const orderedCalendarItem = screen
      .getByText('Ordered calendar event count')
      .closest('div')
    expect(orderedCalendarItem).not.toBeNull()
    await waitFor(() =>
      expect(
        within(orderedCalendarItem as HTMLElement).getByText('0'),
      ).toBeInTheDocument(),
    )

    expect(
      screen.getByRole('link', { name: 'Open active run rankings' }),
    ).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings')
    expect(
      screen.getByRole('link', { name: 'Open active run race' }),
    ).toHaveAttribute('href', '/viewer/runs/run%20alpha/race')
    expect(
      screen.getByRole('link', { name: 'Open active run tournaments' }),
    ).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments')
    expect(
      screen.getByRole('link', { name: 'Open active run calendar' }),
    ).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar')
    expect(
      screen.getByRole('link', { name: 'Open run browser' }),
    ).toHaveAttribute('href', '/viewer/runs')

    expectNoForbiddenViewerActions()
  })
})
