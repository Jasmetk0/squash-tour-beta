import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveRunId } from '../../../test/viewerTestUtils'
import { VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY } from '../../../viewer/activeProductRun'
import { ViewerRankingsPage } from './ViewerRankingsPage'

const api = vi.hoisted(() => ({
  getViewerOfficialRanking: vi.fn()
}))

vi.mock('../../../api/client', () => api)

function renderRankings(): void {
  renderWithViewerProviders(<ViewerRankingsPage />)
}

describe('ViewerRankingsPage', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
  })

  it('renders the no-active-run landing without forbidden Viewer action labels', () => {
    renderRankings()

    expect(screen.getByRole('heading', { level: 2, name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders the canonical current Official Ranking for the selected Product Run', async () => {
    setViewerActiveRunId('legacy alpha')
    localStorage.setItem(VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY, 'run alpha')
    api.getViewerOfficialRanking.mockResolvedValue({
      schema_version: 'viewer_official_ranking.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      season_index: 3,
      week: 14,
      week_ordinal: 196,
      snapshot_fingerprint: 'a'.repeat(64),
      policy_id: 'best-15',
      best_n: 15,
      row_count: 2,
      rows: [
        { rank: 1, player_id: 'player-a', points: 1234 },
        { rank: 2, player_id: 'player-b', points: 987 }
      ]
    })

    renderRankings()

    expect(await screen.findByText('Current Official Ranking')).toBeInTheDocument()
    expect(api.getViewerOfficialRanking).toHaveBeenCalledWith('run alpha')
    expect(screen.getByText('branch-viewer')).toBeInTheDocument()
    expect(screen.getByText('2003')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Current Top 10 Official Ranking table' })).toHaveTextContent('player-a')
    expect(screen.getByRole('table', { name: 'Current Top 10 Official Ranking table' })).toHaveTextContent('1234')
    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings')
    expectNoForbiddenViewerActions()
  })
})
